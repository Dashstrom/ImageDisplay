import os
import sys
import subprocess
import shutil

from typing import Iterator, List, Tuple
from colorama import Fore, Style, init
from PIL import Image, ImageSequence
from time import sleep, time


init()
PIXEL = "█"
COLORS = (
    ((30, 34, 36), Fore.BLACK + Style.DIM),
    ((10, 39, 53), Fore.BLACK + Style.NORMAL),
    ((85, 87, 87), Fore.BLACK + Style.BRIGHT),
    ((160, 160, 160), Fore.WHITE + Style.DIM),
    ((220, 220, 220), Fore.WHITE + Style.NORMAL),
    ((255, 255, 255), Fore.WHITE + Style.BRIGHT),
    ((88, 0, 0), Fore.RED + Style.DIM),
    ((204, 0, 0), Fore.RED + Style.NORMAL),
    ((239, 41, 41), Fore.RED + Style.BRIGHT),
    ((52, 103, 4), Fore.GREEN + Style.DIM),
    ((78, 154, 6), Fore.GREEN + Style.NORMAL),
    ((138, 226, 52), Fore.GREEN + Style.BRIGHT),
    ((131, 107, 0), Fore.YELLOW + Style.DIM),
    ((169, 160, 0), Fore.YELLOW + Style.NORMAL),
    ((252, 233, 79), Fore.YELLOW + Style.BRIGHT),
    ((34, 67, 109), Fore.BLUE + Style.DIM),
    ((52, 101, 164), Fore.BLUE + Style.NORMAL),
    ((173, 127, 168), Fore.BLUE + Style.BRIGHT),
    ((90, 60, 90), Fore.MAGENTA + Style.DIM),
    ((125, 80, 125), Fore.MAGENTA + Style.NORMAL),
    ((190, 130, 190), Fore.MAGENTA + Style.BRIGHT),
    ((4, 101, 103), Fore.CYAN + Style.DIM),
    ((6, 152, 154), Fore.CYAN + Style.NORMAL),
    ((52, 226, 226), Fore.CYAN + Style.BRIGHT)
)

# make palette
if getattr(sys, 'frozen', False):
    PATH = os.path.dirname(sys.executable)
else:
    PATH = os.path.dirname(os.path.realpath(__file__))

PALETTE_PATH = os.path.join(PATH, "palette.png")
try:
    os.remove(PALETTE_PATH)
except FileNotFoundError:
    pass
PALETTE_DATA = [c for rgb, _ in COLORS for c in rgb]
PALETTE_DATA += [*COLORS[0][0]] * (256 - len(COLORS))
PALETTE = Image.new('P', (16, 16))
PALETTE.putpalette(PALETTE_DATA)
for y in range(16):
    for x in range(16):
        PALETTE.putpixel((x, y), x + y * 16)
PALETTE.save(PALETTE_PATH)


def compress(image: Image.Image) -> Image.Image:
    """Reduce color and size for get image with terminale size and colors."""
    image = image.convert("RGB")
    im = image.im.convert("P", 0, PALETTE.im)
    try:
        return image._new(im)
    except AttributeError:
        return image._makeself(im)


def get_terminal_size() -> Tuple[int, int]:
    """Get terminale size."""
    width, height = shutil.get_terminal_size()
    return width - 2, height - 2


def color(pixel: int) -> str:
    """Return the color of a palette index."""
    return COLORS[pixel][1]


def image_to_str(image: Image.Image) -> str:
    """Convert `PIL.Image` into `str`."""
    width, height = get_terminal_size()
    compresed_image = compress(image)
    resized_image = compresed_image.resize((width, height), Image.BILINEAR)
    image_content: List[List[str]] = []
    last = None
    for y in range(resized_image.height):
        image_content.append([])
        for x in range(resized_image.width):
            color_pxl = color(resized_image.getpixel((x, y))) + PIXEL
            image_content[y].append(PIXEL if color_pxl == last else color_pxl)
            last = color_pxl
    return ("\n".join("".join(line) for line in image_content)
            + Style.RESET_ALL)


def video_to_gif(in_path: str, out_path: str):
    """Convert video into gif using ffmpeg and console palette."""
    try:
        process = subprocess.Popen(
            ["ffmpeg", "-i", in_path, "-i", PALETTE_PATH, "-lavfi",
             "paletteuse", "-y", "-r", "10", "-hide_banner", out_path])
        code = process.wait()
        if code != 0:
            raise OSError(f"ffmpeg error: exit with {code}")
    finally:
        process.wait()
        sleep(0.5)


class TerminalImage:
    """Representation of image in terminal."""
    def __init__(self, image: Image.Image) -> None:
        self.frames = []
        self.durations = []
        start_time = time()
        for i, frame in enumerate(ImageSequence.Iterator(image), start=1):
            image_str = image_to_str(image=frame)
            self.durations.append(frame.info.get("duration", 200) / 1000)
            self.frames.append(image_str)
            time_taken = (time() - start_time) * 1000
            info = "\rframe={:4} time={:6.0f}ms chars={:9}"
            print(info.format(i, time_taken, self.chars), end="")

    @staticmethod
    def from_path(path) -> 'TerminalImage':
        """Load image from path."""
        try:
            return TerminalImage(image=Image.open(path))
        except OSError:
            pass
        # failed to load like an basic image
        in_path = os.path.abspath(path)
        out_path = in_path + ".temp.gif"
        print("Start converting video into gif")
        try:
            video_to_gif(in_path, out_path)
            return TerminalImage(image=Image.open(out_path))
        finally:
            try:
                os.remove(out_path)
            except FileNotFoundError:
                pass

    def show(self, animated: bool = False, repeat: int = 0) -> None:
        """Show image in stdout."""
        try:
            if animated:
                frames = self.frames
            else:
                frames = [self.frames[0]]
            if repeat <= -1:
                while True:
                    for i, frame in enumerate(frames):
                        sleep(self.durations[i])
                        print(f"\n\n{frame}")
            else:
                for rep in range(repeat + 1):
                    for i, frame in enumerate(frames):
                        sleep(self.durations[i])
                        print(f"\n\n{frame}")
        except Exception:
            print(Style.RESET_ALL)
            raise

    @property
    def chars(self) -> int:
        """Chars count."""
        return sum(len(frame) for frame in self.frames)

    def __str__(self) -> str:
        return self.frames[0]

    def __repr__(self) -> str:
        return (f"<TerminalImage id={id(self)} frames={len(self.frames)} "
                f"chars={self.chars}>")

    def __len__(self) -> int:
        return len(self.frames)

    def __iter__(self) -> Iterator[str]:
        return self.frames.__iter__()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"SYNTAX: python3 {sys.argv[0]} [path]")
    else:
        img = TerminalImage.from_path(path=sys.argv[1])
        if len(img) > 1:
            img.show(animated=True, repeat=-1)
        else:
            img.show(animated=False, repeat=0)
        sys.exit(0)

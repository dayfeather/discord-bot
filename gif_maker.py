from PIL import Image, ImageSequence

def make_birthday_gif(bg_path, gif_path, output_path, gif_size=(200, 200), pos=None):
    bg = Image.open(bg_path).convert("RGBA")
    gif = Image.open(gif_path)

    frames = []

    for frame in ImageSequence.Iterator(gif):
        frame = frame.convert("RGBA")
        frame = frame.resize(gif_size)

        new_frame = bg.copy()

        if pos is None:
            x = (bg.width - frame.width) // 2
            y = (bg.height - frame.height) // 2
        else:
            x, y = pos

        new_frame.paste(frame, (x, y), frame)
        frames.append(new_frame)

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=gif.info.get("duration", 100),
        loop=0
    )
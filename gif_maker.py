from PIL import Image, ImageSequence

def make_birthday_gif(bg_path, gif_path, output_path):
    bg = Image.open(bg_path).convert("RGBA")
    gif = Image.open(gif_path)

    frames = []

    for frame in ImageSequence.Iterator(gif):
        frame = frame.convert("RGBA")

        # 調整 GIF 大小
        frame = frame.resize((200, 200))

        # 複製背景
        new_frame = bg.copy()

        # 貼上 GIF（位置你可以調）
        new_frame.paste(frame, (150, 100), frame)

        frames.append(new_frame)

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=gif.info.get("duration", 100),
        loop=0
    )
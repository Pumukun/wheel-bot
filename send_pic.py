import os
import sys
import random
import typing

async def get_full(folder_path: str) -> str:
    images = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    if images:
        random_image = random.choice(images)
        return os.path.join(folder_path,random_image)

@dp.message(Command("full"))
async def send_full(message: types.Message):
    image = get_full(image_folder)
    with open(image, "rb") as photo:
        await bot.send_photo(id = message.from_id, photo)


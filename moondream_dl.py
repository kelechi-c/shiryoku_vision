from typing import List
import io
import re
import requests
import os
import pandas as pd
import concurrent
from PIL import Image as pillow_image
from multiprocessing import Pool
from datasets import load_dataset
from tqdm.auto import tqdm
from concurrent.futures import ThreadPoolExecutor

def load_image(url):
    try:
        url_content = requests.get(url, stream=True).raw
        image = pillow_image.open(url_content)
        return image

    except Exception as e:

        print(f"Error loading image: {url}, {e}")
        return None

sample_image = "ignore/images/laptoppic.jpeg"


image_folder = "moondream_images"
out_folder = os.path.join(os.getcwd(), image_folder)


def format_filename(filename):
    name, ext = os.path.splitext(filename)
    pattern = r"[^\w\-]"
    
    formatted_filename = re.sub(pattern, "", name)

    return formatted_filename + ext


def download_img(url):
    try:
        response_file = requests.get(url)
        out_file = format_filename(os.path.basename(url))
        out_path = os.path.join(out_folder, out_file)

        with open(out_path, "wb") as image_file:
            image_file.write(response_file.content)
            yield image_file


    except Exception as e:
        print(f"error: {e}")


def get_moondream_data(split_size: int):
    moondream_dataset = load_dataset("isidentical/moondream2-coyo-5M-captions")
    md_data = moondream_dataset["train"][:split_size]  # type: ignore
    image_urls = md_data["url"]  # type: ignore
    descriptions = md_data["moondream2_caption"]  # type: ignore

    count = 0

    for url, desc in tqdm(zip(image_urls, descriptions), total=split_size):
        url = str(url)
        if url.endswith(("jpeg", "jpg", "png")):

            image_dl = download_img(url)
            caption = desc.lower()
            file_name = format_filename(os.path.basename(url))

            count += 1

        else:
            continue

        if image_dl is not None:
            yield (image_dl, file_name, caption)
            
    print(f"{count} images downloaded")


q, k, v = zip(*get_moondream_data(1000))


def save_images(file_generator):
    for image_file in tqdm(enumerate(file_generator)):
        image_path = os.path.join(out_folder, image_file.name) # type: ignore

        with open(image_path, "rb") as image_file:
            image_buffer = io.BytesIO(image_file.read())

        with open(image_path, "wb") as f:
            f.write(image_buffer.getbuffer())

        image_file.close()


def threaded_image_saving(file_generator, max_workers=4):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(save_images, image_file) for image_file in file_generator
        ]
        for _ in concurrent.futures.as_completed(futures):
            pass



saved_images = [threaded_image_saving(file_gen) for file_gen in q]


csv_path = "moondream_2.csv"

def moondream_csv(path: List, desc: List):
    print("Writing to csv..")

    md_dict = {"image_path": path, "caption": desc}

    moondream_df = pd.DataFrame(md_dict)

    moondream_df.to_csv(csv_path, index=False)

    print("Csv transfer complete...")


moondream_csv(k, v)

print("Moondream to Kaggle porting complete")

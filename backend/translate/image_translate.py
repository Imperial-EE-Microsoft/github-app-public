import cv2
from PIL import Image, ImageDraw, ImageFont, ImageStat
import re
from openai import AzureOpenAI
import json
import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import matplotlib.pyplot as plt
import time
from msrest.authentication import CognitiveServicesCredentials
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from azure.core.credentials import AzureKeyCredential
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from django.conf import settings
from azure.cognitiveservices.vision.computervision import ComputerVisionClient

# Azure Credentials
subscription_key = settings.SUBSCRIPTION_KEY_AZURE_IMAGE
endpoint = settings.ENDPOINT_AZURE_IMAGE


# OpenAI Credentials
api_base = settings.ENDPOINT_IMAGE_TRANSLATION
api_key= settings.API_KEY_IMAGE_TRANSLATION
deployment_name = settings.DEPLOYMENT_NAME_IMAGE_TRANSLATION
api_version = settings.API_VERSION_IMAGE_TRANSLATION

# # Pre-requisites (pip install)
# # !pip install azure-cognitiveservices-vision-computervision matplotlib pillow openai

# use a .ttf font that can support all languages you want to translate to
# e.g. use https://github.com/notofonts/noto-cjk/tree/main/Sans


FIXED_FONT_PATH_FOR_PLOTTING = "./NotoSans-Medium.ttf"
FONT_FOLDER_PATH = settings.FONT_FOLDER_PATH

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential

from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials
import time
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import json
from openai import AzureOpenAI
import re



#---------------------------------------------#
#            Azure Credentials                #
#---------------------------------------------#

# computervision_client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(subscription_key))
openAI_client = AzureOpenAI(
    api_key=api_key,  
    api_version=api_version,
    base_url=f"{api_base}/openai/deployments/{deployment_name}"
)

image_analysis_client = ImageAnalysisClient(endpoint, AzureKeyCredential(subscription_key))


#---------------------------------------------#
#          Image Translation Functions        #
#---------------------------------------------#

# Function to Get Line Bounding Boxes
def get_line_bounding_boxes(image_path):
    """
    Given a path to an image, returns the bounding boxes of each line of text in the image.
    Uses the Azure Image Analysis API.
    """
    with open(image_path, "rb") as image_stream:
        image_data = image_stream.read()
        try:
            result = image_analysis_client.analyze(
            image_data=image_data,
            visual_features=[VisualFeatures.READ],
        )
        except Exception as e:
            print(f"ERROR: {e}, returning empty list of bounding boxes")
            return []
            

    if result.read is not None and len(result.read.blocks) > 0 and len(result.read.blocks[0].lines) > 0:
        line_bounding_boxes = []
        for line in result.read.blocks[0].lines:
            bounding_box = []
            for point in line.bounding_polygon:
                bounding_box.append(point.x)
                bounding_box.append(point.y)
            line_bounding_boxes.append({
                "text": line.text,
                "bounding_box": bounding_box,
                "confidence": line.words[0].confidence if line.words else None
            })
        return line_bounding_boxes
    else:
        return []



def extract_and_save_text_from_image_path(image_path):
    image_name = os.path.basename(image_path).split(".")[0]
    json_path = f"./bounding_boxes/{image_name}.json"
    if os.path.exists(json_path):
        bounding_boxes = load_bounding_boxes(json_path)
        if not os.path.exists(image_path):
            raise Exception(f"Image file {image_path} does not exist.")
    else:
        print(f"Bounding box data {json_path} does not exist. Generating...")
        bounding_boxes = get_line_bounding_boxes(image_path)
    if bounding_boxes:
        save_bounding_boxes(image_path, bounding_boxes)
    else:
        raise Exception("No text was recognized in the image.")


    data = list()
    for bounding_box in bounding_boxes:
        data.append((bounding_box["text"]))

    return data

def extract_text_from_image_path(image_path):
    image_name = os.path.basename(image_path).split(".")[0]
    # json_path = f"./bounding_boxes/{image_name}.json"
    # if os.path.exists(json_path):
        # bounding_boxes = load_bounding_boxes(json_path)
        # if not os.path.exists(image_path):
        #     raise Exception(f"Image file {image_path} does not exist.")
    # else:
    # print(f"Bounding box data {json_path} does not exist. Generating...")
    bounding_boxes = get_line_bounding_boxes(image_path)
    # if bounding_boxes:
    #     save_bounding_boxes(image_path, bounding_boxes)
    # else:
        # raise Exception("No text was recognized in the image.")


    data = list()
    for bounding_box in bounding_boxes:
        data.append((bounding_box["text"]))

    return data


def gen_image_translation_prompt(image_path, language):
    text_data = extract_text_from_image_path(image_path)
    if not text_data:
        raise ValueError("This image does not contain any text.")
    prompt =\
        f'''
You are a translator that receives a batch of lines in an image . Given the following yaml file, please translate each line into {language}. 
For each line, replace it with it's translated version, respecting the context of the text. THE OUTPUT MUST HAVE THE SAME LINES AS THE INPUT, SO PLEASE OUTPUT ONE LINE FOR EVERY LINE.

An example translation to Chinese:
Input:
- Hello World
- Today is a great day
- I like to code
- Python
Output:
- 你好，世界
- 今天是个好日子
- 我喜欢写代码
- Python


Return only the yaml file translated to {language}.
'''

    for line in text_data:
        prompt += f"- {line}\n"
    return prompt


def remove_code_backticks(message):
    match = re.match(r'```(?:\w+)?\n(.*?)\n```', message, re.DOTALL)
    return match.group(1) if match else message


def extract_yaml_lines(message):
    lines = message.split('\n')
    yaml_lines = [line[2:] for line in lines if line.startswith('- ')]
    return yaml_lines


def get_translated_text_data(image_path, language):
    try: 
        prompt = gen_image_translation_prompt(image_path, language)
    except ValueError as e:
        print(e)
        return []

    response = openAI_client.chat.completions.create(
    model=deployment_name,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": [
            {
                "type": "text",
                "text": prompt
            },
        ]}
    ],
    max_tokens=2000
    )
    res = extract_yaml_lines(remove_code_backticks(
        response.choices[0].message.content))
    print(f"Prompt: {prompt}")
    print(f"Response: {res}")
    return res


# Function to get the average color of a bounding box area
def get_average_color(image, bounding_box):
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    pts = [(bounding_box[i], bounding_box[i+1])
           for i in range(0, len(bounding_box), 2)]
    draw.polygon(pts, fill=255)
    stat = ImageStat.Stat(image, mask)
    avg_color = tuple(int(x)
                      for x in stat.mean[:3])  # Ensure it's a tuple of ints
    return avg_color

# Function to determine the grayscale color for text


def get_text_color(bg_color):
    # Using luminance formula to determine if the text should be black or white
    luminance = (0.299*bg_color[0] + 0.587*bg_color[1] + 0.114*bg_color[2])/255
    return (0, 0, 0) if luminance > 0.5 else (255, 255, 255)

# Function to apply perspective warp to text image


def warp_image_to_bounding_box(image, bounding_box, image_width, image_height):
    h, w = image.shape[:2]
    src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst_pts = np.float32([(bounding_box[i], bounding_box[i+1])
                         for i in range(0, len(bounding_box), 2)])
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    try:
        warped = cv2.warpPerspective(image, matrix, (image_width, image_height), flags=cv2.INTER_LANCZOS4)
    except:
        warped = matrix
    return warped

# Function to draw text onto an image


def draw_text_on_image(text, font, text_color):
    # Create an image with transparent background
    size = font.getbbox(text)[2:]  # width and height of the text
    text_image = Image.new('RGBA', size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(text_image)
    draw.text((0, 0), text, font=font, fill=text_color)
    return text_image

# Function to create a filled polygon mask
def create_filled_polygon_mask(bounding_box, image_size, fill_color):
    mask_image = Image.new('RGBA', image_size, (255, 255, 255, 0))
    mask_draw = ImageDraw.Draw(mask_image)
    pts = [(bounding_box[i], bounding_box[i+1])
           for i in range(0, len(bounding_box), 2)]
    mask_draw.polygon(pts, fill=fill_color)
    return mask_image


#-------------------------------------------------#
#    Generate annotated image with translations   #
#-------------------------------------------------#

def create_annotated_image(image_path, line_bounding_boxes, translated_text_list, fontname, plot=False):

    image = Image.open(image_path).convert('RGBA')
    
    font_size = 50
    fontpath = os.path.join('..',FONT_FOLDER_PATH, fontname)
    font = ImageFont.truetype(fontpath, font_size)

    for line_info, translated_text in zip(line_bounding_boxes, translated_text_list):
        bounding_box = line_info['bounding_box']

        # Get the average color of the bounding box area
        bg_color = get_average_color(image, bounding_box)
        text_color = get_text_color(bg_color)

        # Create a mask to fill the bounding box area with the background color
        mask_image = create_filled_polygon_mask(
            bounding_box, image.size, bg_color)

        # Composite the mask onto the image to fill the bounding box
        image = Image.alpha_composite(image, mask_image)

        # Draw the translated text onto a temporary image
        text_image = draw_text_on_image(translated_text, font, text_color)

        # Convert the text image to an array and warp it to fit the bounding box
        text_image_array = np.array(text_image)
        warped_text_image = warp_image_to_bounding_box(
            text_image_array, bounding_box, image.width, image.height)


        # Convert the warped text image back to PIL format and paste it onto the original image
        warped_text_image_pil = Image.fromarray(warped_text_image)
        image = Image.alpha_composite(image, warped_text_image_pil)

    # Create output directories if it doesn't exist
    os.makedirs('./image_tmp/', exist_ok=True)
    os.makedirs('./image_tmp/translated/', exist_ok=True)

    # Save the annotated image
    output_path = os.path.join('./image_tmp/translated/', os.path.basename(image_path))
    print(f"output path is {output_path}")
    image.save(output_path)
    print(f"Annotated image saved to {output_path}")
    

    # Display the image if needed (if called inside a notebook)
    if plot:
        plt.figure(figsize=(20, 10))
        plt.subplot(1, 2, 1)
        plt.imshow(image.convert('RGB'))
        plt.title("Annotated Image with Translated Text")
        plt.axis("off")

        original_image = Image.open(image_path)
        plt.subplot(1, 2, 2)
        plt.imshow(original_image)
        plt.title("Original Image")
        plt.axis("off")

        plt.show()
    
    
    return output_path


#------------------------------------------------#
#            High Level Translations             #
#------------------------------------------------#


def generate_translated_tmp_image(image_path, language, fontname, plot=False):
    print(f"Translating image '{image_path}' for language '{language}'")
    
    return create_annotated_image(image_path, get_line_bounding_boxes(image_path),
                               get_translated_text_data(image_path, language), fontname, plot=False)
    
    # try:
    #     return create_annotated_image(image_path, get_line_bounding_boxes(image_path),
    #                            get_translated_text_data(image_path, language), fontname, plot=False)

    # except Exception as e:
    #     print(
    #         f"An error occurred while translating the image '{image_path}' for language '{language}': {e}")
    #     return None



def translate_image_content(file_content, language, fontname):
    # Step 1: Write the image content to a temporary file
    # stored_directory = "./image_tmp/"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    stored_directory = os.path.join(base_dir, "image_tmp")
    stored_path = os.path.join(stored_directory, "tmp.png")
    
    # Create directory if it does not exist
    if not os.path.exists(stored_directory):
        os.makedirs(stored_directory)
    
    with open(stored_path, 'wb') as file:
        file.write(file_content)

    # Step 2: Use the existing translate_image function
    translated_image_path = generate_translated_tmp_image(stored_path, language, fontname)
    if not translated_image_path:
        return None

    with open(translated_image_path, 'rb') as file:
        content = file.read()
    return content





#----------------------------------------------------#
#   Unused Functions (for the library not the app)   #
#----------------------------------------------------#

# Function to Save Bounding Boxes and Confidence Scores as JSON
def save_bounding_boxes(image_path, bounding_boxes):
    base_name = os.path.basename(image_path)
    name, _ = os.path.splitext(base_name)
    output_dir = "./bounding_boxes"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{name}.json")

    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(bounding_boxes, json_file, ensure_ascii=False, indent=4)

# Function to Load Bounding Boxes and Confidence Scores from JSON
def load_bounding_boxes(json_path):
    with open(json_path, "r", encoding="utf-8") as json_file:
        return json.load(json_file)


# Function to Plot Bounding Boxes on Image. Set display=True to display the image in a notebook.
# Saves images to ./analyzed_images
def plot_bounding_boxes(image_path, line_bounding_boxes, display=True):
    # Create output directory if it doesn't exist
    os.makedirs('./analyzed_images', exist_ok=True)

    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)

    font_size = 20
    font = ImageFont.truetype(FIXED_FONT_PATH_FOR_PLOTTING, font_size)

    for line_info in line_bounding_boxes:
        print(line_info)
        bounding_box = line_info['bounding_box']
        confidence = line_info['confidence']
        pts = [(bounding_box[i], bounding_box[i+1])
               for i in range(0, len(bounding_box), 2)]

        # Draw thicker polygon for bounding box with width parameter
        draw.line(pts + [pts[0]], fill="yellow", width=4)

        # Coordinates for the text
        x, y = bounding_box[0], bounding_box[1] - font_size

        # Draw white text outline
        outline_range = 2
        for dx in range(-outline_range, outline_range + 1):
            for dy in range(-outline_range, outline_range + 1):
                if dx != 0 or dy != 0:
                    draw.text(
                        (x + dx, y + dy), f"{line_info['text']} ({confidence:.2f})", font=font, fill="white")

        # Draw black text
        draw.text(
            (x, y), f"{line_info['text']} ({confidence:.2f})", font=font, fill="black")

    # Save the annotated image
    output_path = os.path.join(
        './analyzed_images', os.path.basename(image_path))
    image.save(output_path)

    if display:
        # Display the image
        plt.figure(figsize=(20, 10))
        plt.subplot(1, 2, 1)
        plt.imshow(np.array(image))
        plt.title("Image with Bounding Boxes")
        plt.axis("off")

        original_image = Image.open(image_path)
        plt.subplot(1, 2, 2)
        plt.imshow(np.array(original_image))
        plt.title("Original Image")
        plt.axis("off")

        plt.show()


# Function to Process Multiple Image Paths
def process_image_paths(image_paths):
    output_dir = "./bounding_boxes"
    os.makedirs(output_dir, exist_ok=True)

    for image_path in image_paths:
        if image_path.lower().endswith(settings.SUPPORTED_IMAGE_EXTENSIONS):
            print(f"Processing {image_path}")
            line_bounding_boxes = get_line_bounding_boxes(image_path)
            if line_bounding_boxes:
                save_bounding_boxes(image_path, line_bounding_boxes)
                plot_bounding_boxes(
                    image_path, line_bounding_boxes, display=True)


def retrieve_bounding_boxes_by_image_path(image_path):
    image_name = os.path.basename(image_path).split(".")[0]
    json_path = f"./bounding_boxes/{image_name}.json"
    if os.path.exists(json_path):
        bounding_boxes = load_bounding_boxes(json_path)
        if os.path.exists(image_path):
            return bounding_boxes
        else:
            print(f"Image file {image_path} does not exist.")
    else:
        print(f"Bounding box data {json_path} does not exist.")



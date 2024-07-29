import asyncio
import shutil
import json
import re
import tempfile
from django.conf import settings
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatCompletion,
    AzureChatCompletion,
)
from semantic_kernel.connectors.ai.prompt_execution_settings import (
    PromptExecutionSettings,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from semantic_kernel.prompt_template.input_variable import InputVariable
from semantic_kernel.prompt_template.prompt_template_config import PromptTemplateConfig
import hashlib
import os
import yaml
from urllib.parse import urlparse
import logging
import tiktoken

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_tokenizer(encoding_name):
    return tiktoken.get_encoding(encoding_name)

def count_tokens(text, tokenizer):
    return len(tokenizer.encode(text))

# split markdown content by code blocks, blockquotes, or html
def split_markdown_content(content, max_tokens, tokenizer):
    chunks = []
    block_pattern = re.compile(r'(```[\s\S]*?```|<.*?>|(?:>\s+.*(?:\n>.*|\n(?!\n))*\n?)+)')
    parts = block_pattern.split(content)
    
    current_chunk = []
    current_length = 0

    for part in parts:
        part_tokens = count_tokens(part, tokenizer)
        
        if current_length + part_tokens <= max_tokens:
            current_chunk.append(part)
            current_length += part_tokens
        else:
            if block_pattern.match(part):
                if current_chunk:
                    chunks.append(''.join(current_chunk))
                chunks.append(part)
                current_chunk = []
                current_length = 0
            else:
                words = part.split()
                for word in words:
                    word_tokens = count_tokens(word + ' ', tokenizer)
                    if current_length + word_tokens > max_tokens:
                        chunks.append(''.join(current_chunk))
                        current_chunk = [word + ' ']
                        current_length = word_tokens
                    else:
                        current_chunk.append(word + ' ')
                        current_length += word_tokens

    if current_chunk:
        chunks.append(''.join(current_chunk))

    return chunks

# high level function to return chunks from md file content
def process_markdown(content, max_tokens=4096, encoding='o200k_base'): # o200k_base is for GPT-4o, cl100k_base is for GPT-4 and GPT-3.5
    tokenizer = get_tokenizer(encoding)
    chunks = split_markdown_content(content, max_tokens, tokenizer)
    
    for i, chunk in enumerate(chunks):
        chunk_tokens = count_tokens(chunk, tokenizer)
        print(f"Chunk {i+1}: Length = {chunk_tokens} tokens")
        if chunk_tokens == max_tokens:
            print("Warning: This chunk has reached the maximum token limit.")
        # print(chunk)
        # print("\n" + "="*80 + "\n")

    return chunks

async def translate(output_lang, input_file, output_file):
    def generate_prompt(output_lang, document_chunk):
        
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(repo_root, "font_language_mappings.yml"), "r") as file:
            mappings = yaml.safe_load(file)
        
        
        is_rtl = mappings.get(output_lang, {}).get('rtl', False)    

        if len(document_chunk.split("\n")) == 1:
            prompt = f"Translate the following text to {output_lang}. NEVER ADD ANY EXTRA CONTENT OUTSIDE THE TRANSLATION. TRANSLATE ONLY WHAT IS GIVEN TO YOU."

        else: 
            prompt = f"""
Translate the following markdown file to {output_lang}.
Make sure the translation does not sound too literal. Make sure you translate comments as well.
Do not translate any entities, such as variable names, function names, or class names, but keep them in the file.
Do not translate any urls or paths, but keep them in the file.
"""
        if is_rtl:
            prompt += "Please write the output from right to left, respecting that this is a right-to-left language.\n"
        else:
            prompt += "Please write the output from left to right.\n"

        prompt += "\n" + document_chunk

        return prompt

    async def run_prompt(prompt, thread_count, i):
        print(f"thread {i}/{thread_count}")
        prompt_template_config = PromptTemplateConfig(
            template=prompt,
            name="translate",
            description="Translate a text to another language",
            template_format="semantic-kernel",
            execution_settings=req_settings,
        )

        function = kernel.add_function(
            function_name="translate_function",
            plugin_name="translate_plugin",
            prompt_template_config=prompt_template_config,
        )

        result = await kernel.invoke(function)
        return result

    kernel = Kernel()

    service_id = "chat-gpt"


    # credentials    
    deployment_name = settings.DEPLOYMENT_NAME_TEXT_TRANSLATION
    endpoint = settings.ENDPOINT_TEXT_TRANSLATION
    api_key = settings.API_KEY_TEXT_TRANSLATION

    kernel.add_service(
        AzureChatCompletion(
            service_id=service_id,
            deployment_name=deployment_name,
            endpoint=endpoint,
            api_key=api_key,
        )
    )

    # Define the request settings
    req_settings = kernel.get_prompt_execution_settings_from_service_id(service_id)
    req_settings.max_tokens = 4096
    req_settings.temperature = 0.7
    req_settings.top_p = 0.8

    with open(input_file, "r") as file:
        document = file.read().strip()

    if not document:
        # If document is empty, just copy the input file to output
        shutil.copyfile(input_file, output_file)
        return

    # Check if there is only one line in the document
    if document.count('\n') == 0:
        # Generate prompt for single line translation
        prompt = f"Translate the following text to {output_lang}. NEVER ADD ANY EXTRA CONTENT OUTSIDE THE TRANSLATION. TRANSLATE ONLY WHAT IS GIVEN TO YOU. MAINTAIN MARKDOWN FORMAT\n\n{document}"

        result = await run_prompt(prompt, 1, 1)

        with open(output_file, "w") as text_file:
            text_file.write(str(result))

        return

    # Split document into chunks (not needed in single line scenario)
    # document_chunks = [document]
    document_chunks = process_markdown(document)
    
    prompts = [
        generate_prompt(output_lang=output_lang, document_chunk=document_chunk)
        for document_chunk in document_chunks
    ]

    with open("prompts.md", "w") as text_file:
        for i, prompt in enumerate(prompts):
            text_file.write(f"-------------- Prompt {i+1} ---------------\n")
            text_file.write(prompt)
            text_file.write("\n\n")

    thread_count = len(prompts)
    results = await asyncio.gather(*[run_prompt(prompt, thread_count, i+1) for i, prompt in enumerate(prompts)])

    with open(output_file, "w") as text_file:
        for result in results:
            text_file.write(str(result))
            text_file.write("\n")
    
        # Add Disclaimer
        text_file.write("\n\n")
        disclaimer_prompt = f""" Translate the following text to {output_lang}.

        Disclaimer: The translation was translated from its original by an AI model and may not be perfect. 
        Please review the output and make any necessary corrections."""
        disclaimer = await run_prompt(disclaimer_prompt, 'disclaimer prompt', 1)
        text_file.write(str(disclaimer))

def update_image_link(md_file_path, markdown_string, language_code, docs_dir):
    logger.info("UPDATING IMAGE LINKS")
    pattern = r'!\[(.*?)\]\((.*?)\)'  # Capture both alt text and link
    matches = re.findall(pattern, markdown_string)

    for alt_text, link in matches:
        parsed_url = urlparse(link)
        if parsed_url.scheme in ('http', 'https'):
            print(f"skipped {link} as it is a URL")
            continue  # Skip web URLs

        # Extract the path without query parameters
        path = parsed_url.path
        original_filename, file_ext = os.path.splitext(os.path.basename(path))

        print(f"link: {link}, original_filename: {original_filename}, file_ext: {file_ext}")
        print("#docs_dir:", docs_dir, "Doc?", md_file_path.startswith(f'{docs_dir}'))

        if file_ext.lower() in settings.SUPPORTED_IMAGE_EXTENSIONS:
            print("this is an image")

            if md_file_path.startswith(f'{docs_dir}'):  # is a docs image
                logger.info(f"this is a docs image for {md_file_path}")
                # Count how many levels to go up
                rel_levels = os.path.relpath(md_file_path, docs_dir).count(os.path.sep) + 2
                rel_path = os.path.relpath(os.path.dirname(md_file_path), docs_dir)
                translated_folder = ('../' * rel_levels) + 'translated_images'
            else:  # is a readme image
                translated_folder = "./translated_images"

            md_file_dir = os.path.dirname(md_file_path)
            actual_image_path = os.path.normpath(os.path.join(md_file_dir, link))
            hash = get_unique_id(actual_image_path)
            new_filename = f"{original_filename}.{hash}.{language_code}{file_ext}"
            updated_link = os.path.join(translated_folder, new_filename)
            if not updated_link.startswith(("/", ".")):
                updated_link = "/" + updated_link
                
            logger.info(f"updated_link: {updated_link}")
            new_image_markup = f'![{alt_text}]({updated_link})'
            markdown_string = re.sub(rf'!\[{re.escape(alt_text)}\]\({re.escape(link)}\)', new_image_markup, markdown_string)
            logger.info(f"markdown_string: {markdown_string}")
        else:
            print(f"file {link} is not an image. Skipping...")
           
    return markdown_string


def get_unique_id(file_path):
    # Convert the file path to bytes
    file_path_bytes = file_path.encode('utf-8')
    
    # Create a SHA-256 hash object
    hash_object = hashlib.sha256()
    
    # Update the hash object with the bytes of the file path
    hash_object.update(file_path_bytes)
    
    # Generate the hexadecimal digest
    unique_identifier = hash_object.hexdigest()
    logger.info(f"HASH in GET UNIQUE ID for: {file_path} HASH={unique_identifier}")
    return unique_identifier

async def translate_and_update(input_string, language, language_code, docs_dir, md_file_path):
    """
    Writes the input string to a temporary markdown file, translates it,
    and returns the translated string.

    Args:
    input_string (str): The string to be translated.
    language (str): The target language for translation.

    Returns:
    str: The translated string.
    """
    # Create a temporary input file
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".md", mode="w"
    ) as temp_input_file:
        temp_input_file_path = temp_input_file.name
        temp_input_file.write(input_string)

    # Create a temporary output file path
    temp_output_file_path = tempfile.mktemp(suffix=".md")

    # Call the translate function
    await translate(language, temp_input_file_path, temp_output_file_path)

    # Read the translated content from the temporary output file
    with open(temp_output_file_path, "r") as temp_output_file:
        translated_content = temp_output_file.read()
        translated_content = update_image_link(md_file_path, translated_content, language_code, docs_dir)

    return translated_content

def translate_string(input_string, language, language_code, docs_dir, md_file_path):
    """
    Wrapper function to run async translate_and_update function synchronously.
    """
    return asyncio.run(translate_and_update(input_string, language, language_code, docs_dir, md_file_path))

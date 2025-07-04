"""
`azure_openai.py` is a module for managing interactions with the Azure OpenAI API within our application.
"""

import base64
import json
import mimetypes
import os
import time
import traceback
from io import BytesIO
from typing import Any, Dict, List, Literal, Optional, Union

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import openai
import requests
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AzureOpenAI

from utils.ml_logging import get_logger

# Load environment variables from .env file
load_dotenv()

# Set up logger
logger = get_logger()


class AzureOpenAIManager:
    """
    A manager class for interacting with the Azure OpenAI API.

    This class provides methods for generating text completions and chat responses using the Azure OpenAI API.
    It also provides methods for validating API configurations and getting the OpenAI client.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        azure_endpoint: Optional[str] = None,
        completion_model_name: Optional[str] = None,
        chat_model_name: Optional[str] = None,
        embedding_model_name: Optional[str] = None,
        dalle_model_name: Optional[str] = None,
        whisper_model_name: Optional[str] = None,
    ):
        """
        Initializes the Azure OpenAI Manager with necessary configurations.

        :param api_key: The Azure OpenAI Key. If not provided, it will be fetched from the environment variable "AZURE_OPENAI_KEY".
        :param api_version: The Azure OpenAI API Version. If not provided, it will be fetched from the environment variable "AZURE_OPENAI_API_VERSION" or default to "2023-05-15".
        :param azure_endpoint: The Azure OpenAI API Endpoint. If not provided, it will be fetched from the environment variable "AZURE_OPENAI_ENDPOINT".
        :param completion_model_name: The Completion Model Deployment ID. If not provided, it will be fetched from the environment variable "AZURE_AOAI_COMPLETION_MODEL_DEPLOYMENT_ID".
        :param chat_model_name: The Chat Model Name. If not provided, it will be fetched from the environment variable "AZURE_AOAI_CHAT_MODEL_NAME".
        :param embedding_model_name: The Embedding Model Deployment ID. If not provided, it will be fetched from the environment variable "AZURE_AOAI_EMBEDDING_DEPLOYMENT_ID".
        :param dalle_model_name: The DALL-E Model Deployment ID. If not provided, it will be fetched from the environment variable "AZURE_AOAI_DALLE_MODEL_DEPLOYMENT_ID".

        """
        self.api_key = api_key or os.getenv("AZURE_OPENAI_KEY")

        self.api_version = (
            api_version or os.getenv("AZURE_OPENAI_API_VERSION") or "2024-02-01"
        )
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.completion_model_name = completion_model_name or os.getenv(
            "AZURE_AOAI_COMPLETION_MODEL_DEPLOYMENT_ID"
        )
        self.chat_model_name = chat_model_name or os.getenv(
            "AZURE_OPENAI_CHAT_DEPLOYMENT_ID"
        )
        self.embedding_model_name = embedding_model_name or os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        )

        self.dalle_model_name = dalle_model_name or os.getenv(
            "AZURE_AOAI_DALLE_MODEL_DEPLOYMENT_ID"
        )

        self.whisper_model_name = whisper_model_name or os.getenv(
            "AZURE_AOAI_WHISPER_MODEL_DEPLOYMENT_ID"
        )

        if not self.api_key:
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
            )
            self.openai_client = AzureOpenAI(
                api_version=self.api_version,
                azure_endpoint=self.azure_endpoint,
                azure_ad_token_provider=token_provider,
            )
        else:
            self.openai_client = AzureOpenAI(
                api_version=self.api_version,
                azure_endpoint=self.azure_endpoint,
                api_key=self.api_key,
            )

        self._validate_api_configurations()

    def get_azure_openai_client(self):
        """
        Returns the OpenAI client.

        This method is used to get the OpenAI client that is used to interact with the OpenAI API.
        The client is initialized with the API key and endpoint when the AzureOpenAIManager object is created.

        :return: The OpenAI client.
        """
        return self.openai_client

    def _validate_api_configurations(self):
        """
        Validates if all necessary configurations are set.

        This method checks if the API key and Azure endpoint are set in the OpenAI client.
        These configurations are necessary for making requests to the OpenAI API.
        If any of these configurations are not set, the method raises a ValueError.

        :raises ValueError: If the API key or Azure endpoint is not set.
        """
        if not all(
            [
                self.openai_client.api_key,
                self.azure_endpoint,
            ]
        ):
            raise ValueError(
                "One or more OpenAI API setup variables are empty. Please review your environment variables and `SETTINGS.md`"
            )

    async def async_generate_chat_completion_response(
        self,
        conversation_history: List[Dict[str, str]],
        query: str,
        system_message_content: str = """You are an AI assistant that
          helps people find information. Please be precise, polite, and concise.""",
        temperature: float = 0.7,
        deployment_name: str = None,
        max_tokens: int = 150,
        seed: int = 42,
        top_p: float = 1.0,
        **kwargs,
    ):
        """
        Asynchronously generates a text completion using Azure OpenAI's Foundation models.
        This method utilizes the chat completion API to respond to queries based on the conversation history.

        :param conversation_history: A list of past conversation messages formatted as dictionaries.
        :param query: The user's current query or message.
        :param system_message_content: Instructions for the AI on how to behave during the completion.
        :param temperature: Controls randomness in the generation, lower values mean less random completions.
        :param max_tokens: The maximum number of tokens to generate.
        :param seed: Seed for random number generator for reproducibility.
        :param top_p: Nucleus sampling parameter controlling the size of the probability mass considered for token generation.
        :return: The generated text completion or None if an error occurs.
        """

        messages_for_api = conversation_history + [
            {"role": "system", "content": system_message_content},
            {"role": "user", "content": query},
        ]

        response = None
        try:
            response = self.openai_client.chat.completions.create(
                model=deployment_name or self.chat_model_name,
                messages=messages_for_api,
                temperature=temperature,
                max_tokens=max_tokens,
                seed=seed,
                top_p=top_p,
                **kwargs,
            )
            # Process and output the completion text
            for event in response:
                if event.choices:
                    event_text = event.choices[0].delta
                    if event_text:
                        print(event_text.content, end="", flush=True)
                        time.sleep(0.01)  # Maintain minimal sleep to reduce latency
        except Exception as e:
            print(f"An error occurred: {str(e)}")

        return response

    def transcribe_audio_with_whisper(
        self,
        audio_file_path: str,
        language: str = "en",
        prompt: str = "Transcribe the following audio file to text.",
        response_format: Literal["json", "text", "srt", "verbose_json", "vtt"] = "text",
        temperature: float = 0.5,
        timestamp_granularities: List[Literal["word", "segment"]] = [],
        extra_headers=None,
        extra_query=None,
        extra_body=None,
        timeout: Union[float, None] = None,
    ):
        """
        Transcribes an audio file using the Whisper model and returns the transcription in the specified format.

        Args:
            audio_file_path: Path to the audio file to transcribe.
            model: ID of the model to use. Currently, only 'whisper-1' is available.
            language: The language of the input audio in ISO-639-1 format.
            prompt: Optional text to guide the model's style or continue a previous audio segment.
            response_format: Format of the transcript output ('json', 'text', 'srt', 'verbose_json', 'vtt').
            temperature: Sampling temperature between 0 and 1 for randomness in output.
            timestamp_granularities: Timestamp granularities ('word', 'segment') for 'verbose_json' format.
            extra_headers: Additional headers for the request.
            extra_query: Additional query parameters for the request.
            extra_body: Additional JSON properties for the request body.
            timeout: Request timeout in seconds.

        Returns:
            Transcription object with the audio transcription.
        """
        try:
            # Create the transcription request
            result = self.openai_client.audio.transcriptions.create(
                file=open(audio_file_path, "rb"),
                model=self.whisper_model_name,
                language=language,
                prompt=prompt,
                response_format=response_format,
                temperature=temperature,
                timestamp_granularities=timestamp_granularities,
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
            )
            return result
        except openai.APIConnectionError as e:
            logger.error("API Connection Error: The server could not be reached.")
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None, None
        except Exception as e:
            logger.error(
                "Unexpected Error: An unexpected error occurred during contextual response generation."
            )
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None, None

    async def generate_chat_response_o1(
        self,
        query: str,
        conversation_history: List[Dict[str, str]] = [],
        max_completion_tokens: int = 5000,
        stream: bool = False,
        model: str = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_01", "o1-preview"),
        **kwargs,
    ) -> Optional[Union[str, Dict[str, Any]]]:
        """
        Generates a text response using the o1-preview or o1-mini models, considering the specific requirements and limitations of these models.

        :param query: The latest query to generate a response for.
        :param conversation_history: A list of message dictionaries representing the conversation history.
        :param max_completion_tokens: Maximum number of tokens to generate. Defaults to 5000.
        :param stream: Whether to stream the response. Defaults to False.
        :param model: The model to use for generating the response. Defaults to "o1-preview".
        :return: The generated text response as a string if response_format is "text", or a dictionary containing the response and conversation history if response_format is "json_object". Returns None if an error occurs.
        """
        start_time = time.time()
        logger.info(
            f"Function generate_chat_response_o1 started at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}"
        )

        try:
            user_message = {"role": "user", "content": query}

            messages_for_api = conversation_history + [user_message]
            logger.info(
                f"Sending request to Azure OpenAI at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}"
            )

            response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages_for_api,
                # max_completion_tokens=max_completion_tokens,
                stream=stream,
                **kwargs,
            )

            if stream:
                response_content = ""
                for event in response:
                    if event.choices:
                        event_text = event.choices[0].delta
                        if event_text is None or event_text.content is None:
                            continue
                        print(event_text.content, end="", flush=True)
                        response_content += event_text.content
                        time.sleep(0.001)  # Maintain minimal sleep to reduce latency
            else:
                response_content = response.choices[0].message.content
                logger.info(f"Model_used: {response.model}")

            conversation_history.append(user_message)
            conversation_history.append(
                {"role": "assistant", "content": response_content}
            )

            end_time = time.time()
            duration = end_time - start_time
            logger.info(
                f"Function generate_chat_response_o1 finished at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))} (Duration: {duration:.2f} seconds)"
            )

            return {
                "response": response_content,
                "conversation_history": conversation_history,
            }

        except openai.APIConnectionError as e:
            logger.error("API Connection Error: The server could not be reached.")
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
        except Exception as e:
            error_message = str(e)
            if "maximum context length" in error_message:
                logger.warning(
                    "Context length exceeded, reducing conversation history and retrying."
                )
                logger.warning(f"Error details: {e}")
                return "maximum context length"
            logger.error(
                "Unexpected Error: An unexpected error occurred during contextual response generation."
            )
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    async def generate_chat_response(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        image_paths: Optional[List[str]] = None,
        image_bytes: Optional[List[bytes]] = None,
        system_message_content: str = (
            "You are an AI assistant that helps people find information. "
            "Please be precise, polite, and concise."
        ),
        temperature: float = 0.7,
        max_tokens: int = 150,
        seed: int = 42,
        top_p: float = 1.0,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Union[str, Dict[str, Any], None] = None,
        response_format: Union[str, Dict[str, Any]] = "text",
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a chat completion from Azure OpenAI, with optional images/tools
        and automatic handling of AOAI's JSON-response requirements.
        """
        start_time = time.time()
        logger.info(
            f"generate_chat_response ⏱️  {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}"
        )

        conversation_history = conversation_history or []

        if tools is not None and tool_choice is None:
            tool_choice = "auto"

        needs_json = (response_format == "json_object") or (
            isinstance(response_format, dict)
            and response_format.get("type") == "json_object"
        )

        if needs_json and "json" not in system_message_content.lower():
            system_message_content = (
                "Respond ONLY with valid JSON. " + system_message_content
            )

        system_msg = {"role": "system", "content": system_message_content}
        if not conversation_history or conversation_history[0] != system_msg:
            conversation_history.insert(0, system_msg)

        # --- user message: text-only vs. multimodal -----------------------
        if image_bytes or image_paths:
            user_msg: Dict[str, Any] = {
                "role": "user",
                "content": [{"type": "text", "text": query}],
            }
            # attach images
            if image_bytes:
                for img in image_bytes:
                    b64 = base64.b64encode(img).decode("utf-8")
                    user_msg["content"].append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        }
                    )
            if image_paths:
                for path in (
                    image_paths if isinstance(image_paths, list) else [image_paths]
                ):
                    try:
                        with open(path, "rb") as fh:
                            b64 = base64.b64encode(fh.read()).decode("utf-8")
                        mime, _ = mimetypes.guess_type(path)
                        mime = mime or "application/octet-stream"
                        user_msg["content"].append(
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{b64}"},
                            }
                        )
                    except Exception as exc:
                        logger.error(f"🔴 image error {path}: {exc}")
        else:
            # plain string so AOAI can scan for the word “json”
            user_msg = {"role": "user", "content": query}

        messages = conversation_history + [user_msg]

        if isinstance(response_format, str):
            response_format_param = {"type": response_format}
        elif isinstance(response_format, dict):
            response_format_param = response_format
        else:
            raise ValueError("response_format must be str or dict")

        logger.info("Sending request to Azure OpenAI …")
        response = self.openai_client.chat.completions.create(
            model=self.chat_model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
            top_p=top_p,
            stream=stream,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format_param,
            **kwargs,
        )

        response_text = ""
        if stream:
            for event in response:
                if (
                    event.choices
                    and event.choices[0].delta
                    and event.choices[0].delta.content
                ):
                    chunk = event.choices[0].delta.content
                    print(chunk, end="", flush=True)
                    response_text += chunk
                    time.sleep(0.001)
        else:
            response_text = response.choices[0].message.content

        conversation_history.extend(
            [user_msg, {"role": "assistant", "content": response_text}]
        )

        logger.info(f"generate_chat_response ✅ in {time.time() - start_time:.2f}s")

        if needs_json:
            try:
                parsed = json.loads(response_text)
                return {
                    "response": parsed,
                    "conversation_history": conversation_history,
                }
            except json.JSONDecodeError as exc:
                logger.error(f"JSON parse failed: {exc}")
                # fall back to raw text
        return {"response": response_text, "conversation_history": conversation_history}

    def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        n: Optional[int] = 1,
        quality: Optional[str] = None,
        response_format: Optional[str] = None,
        size: Optional[str] = None,
        style: Optional[str] = None,
        user: Optional[str] = None,
        extra_headers: Optional[dict] = None,
        extra_query: Optional[dict] = None,
        extra_body: Optional[dict] = None,
        timeout: Optional[float] = None,
        show_picture: Optional[bool] = False,
    ) -> Optional[str]:
        """
        Generates an image for the given prompt using Azure OpenAI's DALL-E model.

        :param prompt: A text description of the desired image(s).
        :param model: The model to use for image generation.
        :param n: The number of images to generate.
        :param quality: The quality of the image that will be generated. 'hd' creates images with finer details and greater consistency across the image.
            This param is only supported for 'dall-e-3'.
        :param response_format: The format in which the generated images are returned.
            Must be one of 'url' or 'b64_json'.
        :param size: The size of the generated images. Must be one of '256x256', '512x512', or '1024x1024' for 'dall-e-2'.
            Must be one of '1024x1024', '1792x1024', or '1024x1792' for 'dall-e-3' models.
        :param style: The style of the generated images. Must be one of 'vivid' or 'natural'.
            'Vivid' causes the model to lean towards generating hyper-real and dramatic images.
            'Natural' causes the model to produce more natural, less hyper-real looking images. This param is only supported for 'dall-e-3'.
        :param user: A unique identifier representing your end-user.
        :param extra_headers: Send extra headers.
        :param extra_query: Add additional query parameters to the request.
        :param extra_body: Add additional JSON properties to the request.
        :param timeout: Override the client-level default timeout for this request, in seconds.
        :return: The URL of the generated image, or None if an error occurred.
        :raises Exception: If an error occurs while making the API request.
        """
        try:
            response = self.openai_client.images.generate(
                prompt=prompt,
                model=model or self.dalle_model_name,
                n=n,
                quality=quality,
                response_format=response_format,
                size=size,
                style=style,
                user=user,
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
            )
            image_url = json.loads(response.model_dump_json())["data"][0]["url"]
            logger.info(f"Generated image URL: {image_url}")

            if show_picture:
                response_image = requests.get(image_url)
                img = mpimg.imread(BytesIO(response_image.content))

                # Create a new figure and add the image to it
                fig = plt.figure(frameon=False)
                ax = plt.Axes(fig, [0.0, 0.0, 1.0, 1.0])
                ax.set_axis_off()
                fig.add_axes(ax)

                # Display the image
                ax.imshow(img, aspect="auto")
                plt.show()

            return image_url
        except openai.APIConnectionError as e:
            logger.error("API Connection Error: The server could not be reached.")
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None, None
        except Exception as e:
            logger.error(
                "Unexpected Error: An unexpected error occurred during contextual response generation."
            )
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None, None

    def generate_embedding(
        self, input_text: str, model_name: Optional[str] = None, **kwargs
    ) -> Optional[str]:
        """
        Generates an embedding for the given input text using Azure OpenAI's Foundation models.

        :param input_text: The text to generate an embedding for.
        :param model_name: The name of the model to use for generating the embedding. If None, the default embedding model is used.
        :param kwargs: Additional parameters for the API request.
        :return: The embedding as a JSON string, or None if an error occurred.
        :raises Exception: If an error occurs while making the API request.
        """
        try:
            response = self.openai_client.embeddings.create(
                input=input_text,
                model=model_name or self.embedding_model_name,
                **kwargs,
            )

            embedding = response.model_dump_json(indent=2)
            logger.info(f"Created embedding: {embedding}")
            return embedding
        except openai.APIConnectionError as e:
            logger.error("API Connection Error: The server could not be reached.")
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None, None
        except Exception as e:
            logger.error(
                "Unexpected Error: An unexpected error occurred during contextual response generation."
            )
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None, None

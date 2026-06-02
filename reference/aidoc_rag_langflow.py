import os
import requests
import json
import uuid
from typing import List, Union, Generator, Iterator
from pydantic import BaseModel, Field


class Pipeline:

    class Valves(BaseModel):
        # ── Langflow connection ──────────────────────────────────────────────
        LANGFLOW_BASE_URL: str = Field(
            default="https://langflow.ai-application.ciisagl.local",
            description="Base URL of your Langflow instance on HPE PCAI."
        )
        LANGFLOW_FLOW_ID: str = Field(
            default="aad75004-2d41-4e63-8bfa-4ea32c760f25",
            description="Flow ID for T1_Ailyn_VectorStoreRAG (from the JSON)."
        )
        LANGFLOW_API_TOKEN: str = Field(
            default="",
            description="Your Langflow API token."
        )

        # ── Qdrant (vector store) ────────────────────────────────────────────
        # apiKey: false in HPE PCAI deployment → leave QDRANT_API_KEY empty
        QDRANT_URL: str = Field(
            default="http://qdrant.ai-application.ciisagl.local",
            description="Full URL of your Qdrant instance on HPE PCAI."
        )
        QDRANT_API_KEY: str = Field(
            default="",
            description="Qdrant API key. Leave empty — HPE PCAI deploys Qdrant with apiKey: false."
        )
        QDRANT_COLLECTION_NAME: str = Field(
            default="test1_allyn",
            description="Qdrant collection name. Must match the collection used during ingestion."
        )

        # ── NVIDIA Embedding model (Qwen3-Embedding-0.6B) ───────────────────
        # From JSON: NVIDIAEmbeddingsComponent-R746e and NVIDIAEmbeddingsComponent-sbPSE
        # Both nodes use the same embedding model and endpoint
        NVIDIA_EMBEDDING_BASE_URL: str = Field(
            default="",
            description="Base URL for the NVIDIA Embeddings endpoint (Qwen3-Embedding-0.6B) on HPE PCAI."
        )
        NVIDIA_EMBEDDING_API_KEY: str = Field(
            default="admin",
            description="API key for the NVIDIA Embeddings endpoint. Default is 'admin' per the flow JSON."
        )
        NVIDIA_EMBEDDING_MODEL: str = Field(
            default="Qwen/Qwen3-Embedding-0.6B",
            description="Embedding model name — taken directly from the flow JSON."
        )

        # ── NVIDIA LLM (Qwen2.5-Coder) ──────────────────────────────────────
        # From JSON: NVIDIAModelComponent-hgFdJ
        NVIDIA_LLM_BASE_URL: str = Field(
            default="",
            description="Base URL for the Qwen2.5-Coder LLM endpoint on HPE PCAI."
        )
        NVIDIA_LLM_API_KEY: str = Field(
            default="",
            description="API key / token for the Qwen2.5-Coder LLM endpoint."
        )
        NVIDIA_LLM_MODEL: str = Field(
            default="qwen/qwen2.5-coder-7b-instruct",
            description="LLM model name as registered in the HPE PCAI NVIDIA NIM."
        )

        # ── RAG / generation settings ────────────────────────────────────────
        # From JSON: SplitText-AYegj node
        CHUNK_SIZE: int = Field(
            default=1000,
            description="Characters per chunk — from SplitText node in the flow."
        )
        CHUNK_OVERLAP: int = Field(
            default=200,
            description="Overlap between chunks — from SplitText node in the flow."
        )
        # From JSON: QdrantVectorStoreComponent-irEc8 node
        NUMBER_OF_RESULTS: int = Field(
            default=4,
            description="How many chunks to retrieve from Qdrant per query."
        )
        # From JSON: NVIDIAModelComponent-hgFdJ node
        LLM_TEMPERATURE: float = Field(
            default=0.1,
            description="LLM temperature — from NVIDIAModelComponent node in the flow."
        )

        # ── SSL ──────────────────────────────────────────────────────────────
        VERIFY_SSL: bool = Field(
            default=False,
            description="Set to False for self-signed certs (common in HPE PCAI / Ezmeral)."
        )

    # ── Prompt template ──────────────────────────────────────────────────────
    # From JSON: Prompt-ELfkN node
    # Original template uses {context} and {question} variables
    PROMPT_TEMPLATE = (
        "{context}\n\n"
        "---\n\n"
        "Given the context above, answer the question as best as possible.\n\n"
        "Question: {question}\n\n"
        "Answer:"
    )

    def __init__(self):
        self.valves = self.Valves()
        self.name = "AIDOC RAG — T1_Ailyn_VectorStoreRAG"

    async def on_startup(self):
        print(f"on_startup: {self.name}")

    async def on_shutdown(self):
        print(f"on_shutdown: {self.name}")

    # ────────────────────────────────────────────────────────────────────────
    # MAIN PIPE
    # Mirrors the Langflow flow graph from T1_Ailyn_VectorStoreRAG.json:
    #
    #   INGEST FLOW (run once to load documents):
    #   File-pnQUK → SplitText-AYegj → QdrantVectorStoreComponent-sbPSE
    #                                    ↑ NVIDIAEmbeddingsComponent-R746e
    #
    #   QUERY FLOW (runs on every chat message):
    #   ChatInput-edhS3 → QdrantVectorStoreComponent-irEc8 → parser-L90v9
    #                      ↑ NVIDIAEmbeddingsComponent-sbPSE
    #   parser-L90v9 → Prompt-ELfkN → NVIDIAModelComponent-hgFdJ → ChatOutput-dcEZY
    # ────────────────────────────────────────────────────────────────────────
    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:

        print(f"[AIDOC RAG] Pipe called — query: {user_message}")

        try:
            # ── STEP 1: Call Langflow API ────────────────────────────────────
            # Triggers the full query flow inside Langflow:
            # embed query → search Qdrant → parse results → build prompt → LLM answer
            url = (
                f"{self.valves.LANGFLOW_BASE_URL}"
                f"/api/v1/run/{self.valves.LANGFLOW_FLOW_ID}"
            )
            headers = {
                "Authorization": f"Bearer {self.valves.LANGFLOW_API_TOKEN}",
                "Content-Type": "application/json",
            }

            # session_id keeps conversation context across turns
            session_id = body.get("chat_id", str(uuid.uuid4()))

            payload = {
                "output_type": "chat",
                "input_type": "chat",
                "input_value": user_message,
                "session_id": session_id,

                # ── Tweaks ───────────────────────────────────────────────────
                # Node IDs extracted directly from T1_Ailyn_VectorStoreRAG.json
                # These override the default values in the flow at runtime
                "tweaks": {

                    # ChatInput node — entry point of the query flow
                    "ChatInput-edhS3": {
                        "input_value": user_message,
                        "session_id": session_id,
                    },

                    # SplitText node — chunk settings for document ingestion
                    "SplitText-AYegj": {
                        "chunk_size": self.valves.CHUNK_SIZE,
                        "chunk_overlap": self.valves.CHUNK_OVERLAP,
                        "separator": "",
                    },

                    # Qdrant INGEST node — stores embedded document chunks
                    "QdrantVectorStoreComponent-sbPSE": {
                        "url": self.valves.QDRANT_URL,
                        "api_key": self.valves.QDRANT_API_KEY,
                        "collection_name": self.valves.QDRANT_COLLECTION_NAME,
                        "distance_func": "Cosine",
                    },

                    # Qdrant SEARCH node — retrieves top-k relevant chunks
                    "QdrantVectorStoreComponent-irEc8": {
                        "url": self.valves.QDRANT_URL,
                        "api_key": self.valves.QDRANT_API_KEY,
                        "collection_name": self.valves.QDRANT_COLLECTION_NAME,
                        "number_of_results": self.valves.NUMBER_OF_RESULTS,
                        "distance_func": "Cosine",
                    },

                    # Parser node — converts Qdrant Data objects into plain text
                    # mode=Stringify joins all retrieved chunks into one string
                    "parser-L90v9": {
                        "mode": "Stringify",
                        "pattern": "Text: {text}",
                        "clean_data": True,
                    },

                    # Prompt node — injects {context} + {question} into the template
                    "Prompt-ELfkN": {
                        "template": self.PROMPT_TEMPLATE,
                    },

                    # NVIDIA Embeddings INGEST side — embeds document chunks
                    # Uses Qwen3-Embedding-0.6B as confirmed in the flow JSON
                    "NVIDIAEmbeddingsComponent-R746e": {
                        "base_url": self.valves.NVIDIA_EMBEDDING_BASE_URL,
                        "nvidia_api_key": self.valves.NVIDIA_EMBEDDING_API_KEY,
                        "model": self.valves.NVIDIA_EMBEDDING_MODEL,
                    },

                    # NVIDIA Embeddings SEARCH side — embeds the user query
                    # Must use the same model as the ingest side
                    "NVIDIAEmbeddingsComponent-sbPSE": {
                        "base_url": self.valves.NVIDIA_EMBEDDING_BASE_URL,
                        "nvidia_api_key": self.valves.NVIDIA_EMBEDDING_API_KEY,
                        "model": self.valves.NVIDIA_EMBEDDING_MODEL,
                    },

                    # NVIDIA LLM node — generates the final answer
                    # Model: qwen/qwen2.5-coder-7b-instruct on HPE PCAI
                    "NVIDIAModelComponent-hgFdJ": {
                        "base_url": self.valves.NVIDIA_LLM_BASE_URL,
                        "api_key": self.valves.NVIDIA_LLM_API_KEY,
                        "model_name": self.valves.NVIDIA_LLM_MODEL,
                        "temperature": self.valves.LLM_TEMPERATURE,
                        "stream": False,
                    },

                    # ChatOutput node — formats the reply back to Open WebUI
                    "ChatOutput-dcEZY": {
                        "sender_name": "AIDOC",
                    },
                },
            }

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                verify=self.valves.VERIFY_SSL,
            )
            response.raise_for_status()
            response_json = response.json()

            # ── STEP 2: Extract answer from Langflow response ────────────────
            # Response path: outputs[0] → outputs[0] → results → message → data → text
            try:
                result_text = (
                    response_json["outputs"][0]["outputs"][0]
                    ["results"]["message"]["data"]["text"]
                )
                return result_text

            except (KeyError, IndexError, TypeError) as e:
                print(f"[AIDOC RAG] Could not parse response structure: {e}")
                return (
                    f"Error: could not parse Langflow response.\n"
                    f"Raw response: {response.text}"
                )

        except requests.exceptions.RequestException as e:
            return f"Error calling Langflow API: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"

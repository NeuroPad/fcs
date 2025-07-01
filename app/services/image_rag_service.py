import os
from typing import List, Dict, Optional, Union
from pathlib import Path
import logging
from PIL import Image
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore

from llama_index.core import StorageContext
from transformers import CLIPProcessor, CLIPModel
import torch
from io import BytesIO

logger = logging.getLogger(__name__)


class ImageRAGService:
    def __init__(
        self,
        chroma_db_path: str = "./chroma_db",
        collection_name: str = "markdown_images",
        markdown_dir: Path = None,
    ):
        """
        Initialize the Image RAG Service

        Args:
            chroma_db_path: Path to store ChromaDB files
            collection_name: Name of the ChromaDB collection
            markdown_dir: Directory containing markdown files and images
        """
        self.markdown_dir = markdown_dir
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Initialize CLIP
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(
            self.device
        )
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

        # Initialize ChromaDB with persistent client
        self.chroma_client = chromadb.PersistentClient(path=chroma_db_path)

        # Create or get collection with proper configuration
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Using collection: {collection_name}")

        # Initialize LlamaIndex vector store
        self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )

    def _get_image_embedding(self, image: Image.Image) -> List[float]:
        """
        Generate CLIP embeddings for an image

        Args:
            image: PIL Image object

        Returns:
            List of float values representing the image embedding
        """
        inputs = self.processor(text=None, images=image, return_tensors="pt")[
            "pixel_values"
        ].to(self.device)

        with torch.no_grad():
            embedding = self.model.get_image_features(inputs)

        return embedding.cpu().numpy()[0].tolist()

    def extract_images_from_markdown(self) -> List[Dict[str, str]]:
        """
        Extract all image paths from the markdown directory

        Returns:
            List of dictionaries containing image information
        """
        images = []

        # Look for images in the images subdirectory
        images_dir = self.markdown_dir
        if images_dir.exists():
            for doc_dir in images_dir.iterdir():
                if doc_dir.is_dir():
                    doc_name = doc_dir.name
                    for img_path in doc_dir.glob("*.png"):
                        images.append(
                            {
                                "path": str(img_path),
                                "doc_name": doc_name,
                                "image_name": img_path.name,
                            }
                        )

        logger.info(f"Found {len(images)} images in markdown directory")
        return images

    def index_markdown_images(self) -> Dict[str, Union[bool, int, List]]:
        """
        Index all images found in the markdown directory

        Returns:
            Dictionary containing indexing results and any errors
        """
        if not self.markdown_dir:
            raise ValueError("Markdown directory not set")

        images = self.extract_images_from_markdown()
        indexed_count = 0
        errors = []

        # Process images in batches for better performance
        batch_size = 10
        for i in range(0, len(images), batch_size):
            batch = images[i : i + batch_size]
            embeddings = []
            ids = []
            metadatas = []

            for img_info in batch:
                try:
                    # Generate embedding
                    image = Image.open(img_info["path"]).convert("RGB")
                    embedding = self._get_image_embedding(image)

                    # Prepare batch data
                    embeddings.append(embedding)
                    ids.append(img_info["image_name"])
                    metadatas.append(
                        {
                            "doc_name": img_info["doc_name"],
                            "image_name": img_info["image_name"],
                            "image_path": img_info["path"],
                        }
                    )

                    indexed_count += 1

                except Exception as e:
                    errors.append({"image_path": img_info["path"], "error": str(e)})
                    logger.error(f"Error indexing image {img_info['path']}: {str(e)}")

            # Batch upsert to ChromaDB
            if embeddings:
                self.collection.upsert(
                    embeddings=embeddings, ids=ids, metadatas=metadatas
                )

        return {
            "success": True,
            "indexed_count": indexed_count,
            "total_images": len(images),
            "errors": errors,
        }

    def find_similar_images(
        self, image_data: bytes, top_k: int = 5
    ) -> Dict[str, Union[bool, List[Dict[str, Union[str, float]]], Optional[str]]]:
        """
        Find similar images using an input image

        Args:
            image_data: Binary image data
            top_k: Number of similar images to return

        Returns:
            Dictionary containing search results or error information
        """
        try:
            # Process query image
            image = Image.open(BytesIO(image_data)).convert("RGB")
            query_embedding = self._get_image_embedding(image)

            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding], n_results=top_k
            )

            # Format results
            similar_images = []
            for i in range(len(results["ids"][0])):
                similar_images.append(
                    {
                        "image_name": results["ids"][0][i],
                        "doc_name": results["metadatas"][0][i]["doc_name"],
                        "similarity_score": 1.0
                        - float(
                            results["distances"][0][i]
                        ),  # Convert distance to similarity
                        "image_path": results["metadatas"][0][i]["image_path"],
                    }
                )

            return {"success": True, "similar_images": similar_images}

        except Exception as e:
            logger.error(f"Error finding similar images: {str(e)}")
            return {"success": False, "error": str(e), "similar_images": []}

    def get_indexed_images(
        self,
    ) -> Dict[str, Union[bool, int, List[Dict[str, str]], Optional[str]]]:
        """
        Get all indexed images information

        Returns:
            Dictionary containing all indexed images or error information
        """
        try:
            # Get collection stats
            count = self.collection.count()

            # Get all image metadata
            results = self.collection.get()

            images = [
                {
                    "image_name": id,
                    "doc_name": metadata["doc_name"],
                    "image_path": metadata["image_path"],
                }
                for id, metadata in zip(results["ids"], results["metadatas"])
            ]

            return {"success": True, "total_images": count, "images": images}

        except Exception as e:
            logger.error(f"Error getting indexed images: {str(e)}")
            return {"success": False, "error": str(e), "images": []}

    def delete_document_images(self, document_name: str):
        """Delete all images associated with a document from the vector store"""
        try:
            # Get all images metadata
            collection = self.chroma_client.get_collection(name="markdown_images")
            # Delete where document_name matches

            collection.delete(where={"doc_name": document_name})
        except Exception as e:
            logger.error(
                f"Error deleting images for document {document_name}: {str(e)}"
            )
            raise

    def has_indexed_images(self, document_name: str) -> bool:
        """Check if a document has any images indexed in ChromaDB"""
        try:
            # Get collection and check for any entries matching the document name
            collection = self.chroma_client.get_collection(name="markdown_images")
            results = collection.get(where={"doc_name": document_name})
            # If we got any results, the document has indexed images
            return len(results["ids"]) > 0
        except Exception as e:
            logger.error(
                f"Error checking indexed images for document {document_name}: {str(e)}"
            )
            return False

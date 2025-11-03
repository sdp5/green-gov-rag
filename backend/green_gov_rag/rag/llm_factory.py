"""LLM Provider Factory for multi-platform support.

Supports OpenAI, Azure OpenAI, AWS Bedrock, and Anthropic.
Uses LangChain for abstraction across providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from green_gov_rag.config import settings
from green_gov_rag.types import LLMProvider

if TYPE_CHECKING:
    from langchain.schema.language_model import BaseLanguageModel


class LLMFactory:
    """Factory for creating LLM instances based on provider configuration."""

    @staticmethod
    def create_llm(
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 500,
    ) -> BaseLanguageModel:
        """Create an LLM instance based on the provider.

        Args:
        ----
            provider: LLM provider (openai, azure, bedrock, anthropic).
                     Defaults to settings.llm_provider
            model: Model name. Defaults to settings.llm_model
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
        -------
            LangChain BaseLanguageModel instance

        Raises:
        ------
            ValueError: If provider is not supported or required credentials are missing

        """
        provider = provider or settings.llm_provider
        model = model or settings.llm_model

        if provider == LLMProvider.OPENAI:
            return LLMFactory._create_openai(model, temperature, max_tokens)
        elif provider == LLMProvider.AZURE:
            return LLMFactory._create_azure_openai(model, temperature, max_tokens)
        elif provider == LLMProvider.BEDROCK:
            return LLMFactory._create_bedrock(model, temperature, max_tokens)
        elif provider == LLMProvider.ANTHROPIC:
            return LLMFactory._create_anthropic(model, temperature, max_tokens)
        else:
            msg = f"Unsupported LLM provider: {provider}"
            raise ValueError(msg)

    @staticmethod
    def _create_openai(
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> BaseLanguageModel:
        """Create OpenAI LLM instance."""
        from langchain_openai import ChatOpenAI
        from pydantic import SecretStr

        if not settings.openai_api_key:
            msg = "OPENAI_API_KEY is required for OpenAI provider"
            raise ValueError(msg)

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            api_key=SecretStr(settings.openai_api_key),
        )

    @staticmethod
    def _create_azure_openai(
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> BaseLanguageModel:
        """Create Azure OpenAI LLM instance."""
        from langchain_openai import AzureChatOpenAI
        from pydantic import SecretStr

        if not settings.azure_openai_api_key or not settings.azure_openai_endpoint:
            msg = "AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT are required for Azure provider"
            raise ValueError(msg)

        deployment_name = settings.azure_openai_deployment or model

        return AzureChatOpenAI(
            azure_deployment=deployment_name,
            model=model,
            temperature=temperature,
            # max_tokens parameter removed - causes empty responses with some models
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=SecretStr(settings.azure_openai_api_key),
            api_version=settings.azure_openai_api_version,
        )

    @staticmethod
    def _create_bedrock(
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> BaseLanguageModel:
        """Create AWS Bedrock LLM instance."""
        from langchain_aws import ChatBedrock
        from pydantic import SecretStr

        if not settings.aws_access_key_id or not settings.aws_secret_access_key:
            msg = "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required for Bedrock provider"
            raise ValueError(msg)

        model_id = settings.bedrock_model_id or model

        return ChatBedrock(
            model=model_id,
            model_kwargs={
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            credentials_profile_name=None,
            aws_access_key_id=SecretStr(settings.aws_access_key_id),
            aws_secret_access_key=SecretStr(settings.aws_secret_access_key),
            region=settings.aws_region,
        )

    @staticmethod
    def _create_anthropic(
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> BaseLanguageModel:
        """Create Anthropic LLM instance."""
        from langchain_anthropic import ChatAnthropic
        from pydantic import SecretStr

        if not settings.anthropic_api_key:
            msg = "ANTHROPIC_API_KEY is required for Anthropic provider"
            raise ValueError(msg)

        return ChatAnthropic(
            model_name=model,
            temperature=temperature,
            max_tokens_to_sample=max_tokens,
            timeout=None,
            stop=None,
            api_key=SecretStr(settings.anthropic_api_key),
        )


def get_llm(
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 500,
) -> BaseLanguageModel:
    """Convenience function to get an LLM instance.

    Args:
    ----
        provider: LLM provider (openai, azure, bedrock, anthropic)
        model: Model name
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response

    Returns:
    -------
        LangChain BaseLanguageModel instance

    """
    return LLMFactory.create_llm(provider, model, temperature, max_tokens)

#!/usr/bin/env python3
"""
dsh-can-see 自定义提供商示例

演示如何接入 Ollama / LocalAI / Azure OpenAI 等第三方服务。
运行：python examples/custom_providers.py
"""

import os
import sys
from pathlib import Path

# 让示例可以 import 到仓库根目录下的 vision_provider 模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vision_provider import VisionProvider


def example_1_ollama():
    """示例 1: 注册并使用 Ollama 本地模型"""
    print("\n" + "="*60)
    print("示例 1: 使用 Ollama 本地视觉模型")
    print("="*60)
    
    # 注册 Ollama 提供商
    VisionProvider.register_custom_provider(
        name="ollama",
        base_url="http://localhost:11434/v1",
        default_model="llava:latest",
        message_format="openai"  # Ollama 兼容 OpenAI 格式
    )
    
    # 使用注册的提供商
    provider = VisionProvider(provider="ollama")
    
    result = provider.analyze_image(
        image_path="test.jpg",
        prompt="请描述这张图片"
    )
    
    if result["success"]:
        print(f"✓ Ollama 分析成功")
        print(f"内容: {result['content']}")
    else:
        print(f"✗ 失败: {result['error']}")


def example_2_azure_openai():
    """示例 2: 注册并使用 Azure OpenAI"""
    print("\n" + "="*60)
    print("示例 2: 使用 Azure OpenAI 视觉模型")
    print("="*60)
    
    # 注册 Azure OpenAI
    VisionProvider.register_custom_provider(
        name="azure",
        base_url="https://your-resource.openai.azure.com",
        default_model="gpt-4o",
        message_format="openai",
        headers={
            "api-key": "your-azure-api-key"  # Azure 使用 api-key 而不是 Bearer token
        }
    )
    
    # 使用 Azure OpenAI
    provider = VisionProvider(
        provider="azure",
        api_key="your-azure-api-key"  # 或通过环境变量 AZURE_API_KEY
    )
    
    result = provider.analyze_image(
        image_path="test.jpg",
        prompt="Describe this image in detail"
    )
    
    if result["success"]:
        print(f"✓ Azure OpenAI 分析成功")
        print(f"内容: {result['content']}")


def example_3_custom_api():
    """示例 3: 使用完全自定义的 API"""
    print("\n" + "="*60)
    print("示例 3: 使用自定义视觉 API")
    print("="*60)
    
    # 注册自定义 API
    VisionProvider.register_custom_provider(
        name="my_vision_api",
        base_url="https://api.example.com/v1",
        default_model="vision-model-v1",
        message_format="openai",  # 使用 OpenAI 兼容格式
        api_key="your-custom-api-key",
        headers={
            "X-Custom-Header": "custom-value"
        }
    )
    
    # 使用自定义提供商
    provider = VisionProvider(provider="my_vision_api")
    
    result = provider.analyze_image(
        image_path="test.jpg",
        prompt="分析这张图片"
    )
    
    if result["success"]:
        print(f"✓ 自定义 API 调用成功")
        print(f"内容: {result['content']}")


def example_4_localai():
    """示例 4: 使用 LocalAI"""
    print("\n" + "="*60)
    print("示例 4: 使用 LocalAI 本地部署")
    print("="*60)
    
    VisionProvider.register_custom_provider(
        name="localai",
        base_url="http://localhost:8080/v1",
        default_model="gpt-4-vision-preview",
        message_format="openai"
    )
    
    provider = VisionProvider(provider="localai")
    
    result = provider.analyze_image(
        image_path="test.jpg",
        prompt="What's in this image?"
    )
    
    if result["success"]:
        print(f"✓ LocalAI 分析成功")
        print(f"内容: {result['content']}")


def example_5_together_ai():
    """示例 5: 使用 Together AI"""
    print("\n" + "="*60)
    print("示例 5: 使用 Together AI 视觉模型")
    print("="*60)
    
    VisionProvider.register_custom_provider(
        name="together",
        base_url="https://api.together.xyz/v1",
        default_model="meta-llama/Llama-Vision-Free",
        message_format="openai"
    )
    
    provider = VisionProvider(
        provider="together",
        api_key="your-together-api-key"  # 或设置 TOGETHER_API_KEY 环境变量
    )
    
    result = provider.analyze_image(
        image_path="test.jpg",
        prompt="Describe this image"
    )
    
    if result["success"]:
        print(f"✓ Together AI 分析成功")
        print(f"内容: {result['content']}")


def example_6_list_and_manage():
    """示例 6: 列出和管理自定义提供商"""
    print("\n" + "="*60)
    print("示例 6: 管理自定义提供商")
    print("="*60)
    
    # 注册几个提供商
    VisionProvider.register_custom_provider(
        name="provider1",
        base_url="http://localhost:8000",
        default_model="model1",
        message_format="openai"
    )
    
    VisionProvider.register_custom_provider(
        name="provider2",
        base_url="http://localhost:9000",
        default_model="model2",
        message_format="openai"
    )
    
    # 列出所有自定义提供商
    custom_providers = VisionProvider.list_custom_providers()
    print(f"已注册的自定义提供商: {custom_providers}")
    
    # 注销一个提供商
    VisionProvider.unregister_custom_provider("provider1")
    
    # 再次列出
    custom_providers = VisionProvider.list_custom_providers()
    print(f"注销后的提供商列表: {custom_providers}")


def example_7_replicate():
    """示例 7: 使用 Replicate"""
    print("\n" + "="*60)
    print("示例 7: 使用 Replicate 视觉模型")
    print("="*60)
    
    # 注意: Replicate 的 API 格式可能需要特殊处理
    # 这里展示基本的注册方式
    VisionProvider.register_custom_provider(
        name="replicate",
        base_url="https://api.replicate.com/v1",
        default_model="yorickvp/llava-13b",
        message_format="custom",  # 可能需要自定义格式
        headers={
            "Authorization": "Token your-replicate-token"
        }
    )
    
    print("✓ Replicate 提供商已注册")
    print("注意: Replicate 可能需要特殊的 API 格式处理")


def example_8_huggingface():
    """示例 8: 使用 HuggingFace Inference API"""
    print("\n" + "="*60)
    print("示例 8: 使用 HuggingFace Inference API")
    print("="*60)
    
    VisionProvider.register_custom_provider(
        name="huggingface",
        base_url="https://api-inference.huggingface.co/models",
        default_model="nlpconnect/vit-gpt2-image-captioning",
        message_format="custom",
        headers={
            "Authorization": "Bearer your-hf-token"
        }
    )
    
    print("✓ HuggingFace 提供商已注册")
    print("注意: HuggingFace 的 API 格式与 OpenAI 不同，可能需要额外适配")


def example_9_env_variable_api_key():
    """示例 9: 使用环境变量配置 API Key"""
    print("\n" + "="*60)
    print("示例 9: 使用环境变量配置自定义提供商")
    print("="*60)
    
    # 注册提供商（不提供 api_key）
    VisionProvider.register_custom_provider(
        name="my_provider",
        base_url="https://api.example.com/v1",
        default_model="vision-v1",
        message_format="openai"
    )
    
    # API Key 将从环境变量 MY_PROVIDER_API_KEY 读取
    # 在使用前设置: export MY_PROVIDER_API_KEY="your-key"
    
    try:
        provider = VisionProvider(provider="my_provider")
        print(f"✓ 从环境变量读取 API Key 成功")
    except ValueError as e:
        print(f"需要设置环境变量: MY_PROVIDER_API_KEY")


def example_10_multiple_models():
    """示例 10: 同一提供商使用不同模型"""
    print("\n" + "="*60)
    print("示例 10: 同一提供商切换不同模型")
    print("="*60)
    
    VisionProvider.register_custom_provider(
        name="multi_model",
        base_url="http://localhost:11434/v1",
        default_model="llava:7b",
        message_format="openai"
    )
    
    # 使用默认模型
    provider1 = VisionProvider(provider="multi_model")
    print(f"Provider 1 使用模型: {provider1.model}")
    
    # 使用不同的模型
    provider2 = VisionProvider(
        provider="multi_model",
        model="llava:13b"
    )
    print(f"Provider 2 使用模型: {provider2.model}")


def main():
    """运行所有自定义提供商示例"""
    print("\n" + "="*60)
    print("自定义视觉模型提供商使用示例")
    print("="*60)
    
    examples = [
        ("Ollama 本地模型", example_1_ollama),
        ("Azure OpenAI", example_2_azure_openai),
        ("自定义 API", example_3_custom_api),
        ("LocalAI", example_4_localai),
        ("Together AI", example_5_together_ai),
        ("管理提供商", example_6_list_and_manage),
        ("Replicate", example_7_replicate),
        ("HuggingFace", example_8_huggingface),
        ("环境变量配置", example_9_env_variable_api_key),
        ("多模型切换", example_10_multiple_models),
    ]
    
    print("\n可用示例:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")
    
    print("\n提示:")
    print("- 大部分本地服务需要先启动相应的服务")
    print("- 云服务需要配置相应的 API Key")
    print("- 环境变量格式: {PROVIDER_NAME}_API_KEY")
    
    # 取消注释以运行特定示例
    # example_1_ollama()
    # example_6_list_and_manage()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
dsh-can-see 基础使用示例

运行：python examples/basic_usage.py
"""

import os
import sys
from pathlib import Path

# 让示例可以 import 到仓库根目录下的 vision_provider 模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vision_provider import VisionProvider


def example_1_basic_usage():
    """示例 1: 基本使用"""
    print("\n" + "="*60)
    print("示例 1: 基本使用 - 分析单张图片")
    print("="*60)
    
    provider = VisionProvider(
        provider="openai",
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o"
    )
    
    result = provider.analyze_image(
        image_path="test_image.jpg",
        prompt="请详细描述这张图片的内容"
    )
    
    if result["success"]:
        print(f"\n✓ 分析成功！")
        print(f"模型: {result['model']}")
        print(f"内容:\n{result['content']}")
        print(f"\nToken 使用: {result['usage']}")
    else:
        print(f"✗ 分析失败: {result['error']}")


def example_2_multiple_images():
    """示例 2: 分析多张图片"""
    print("\n" + "="*60)
    print("示例 2: 分析多张图片")
    print("="*60)
    
    provider = VisionProvider(provider="openai")
    
    result = provider.analyze_images(
        image_paths=["image1.jpg", "image2.jpg"],
        prompt="比较这两张图片的异同，找出它们的共同点和不同点"
    )
    
    if result["success"]:
        print(f"✓ 对比分析完成")
        print(f"分析了 {result['metadata']['image_count']} 张图片")
        print(f"\n结果:\n{result['content']}")


def example_3_url_image():
    """示例 3: 分析 URL 图片"""
    print("\n" + "="*60)
    print("示例 3: 从 URL 分析图片")
    print("="*60)
    
    provider = VisionProvider(provider="openai")
    
    result = provider.analyze_image_url(
        image_url="https://example.com/image.jpg",
        prompt="这张图片里有什么？"
    )
    
    if result["success"]:
        print(f"✓ URL 图片分析完成")
        print(f"{result['content']}")


def example_4_anthropic():
    """示例 4: 使用 Anthropic Claude"""
    print("\n" + "="*60)
    print("示例 4: 使用 Anthropic Claude 3")
    print("="*60)
    
    provider = VisionProvider(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022"
    )
    
    result = provider.analyze_image(
        image_path="document.jpg",
        prompt="请提取这份文档中的所有文字内容（OCR）"
    )
    
    if result["success"]:
        print(f"✓ OCR 完成")
        print(f"{result['content']}")


def example_5_google_gemini():
    """示例 5: 使用 Google Gemini"""
    print("\n" + "="*60)
    print("示例 5: 使用 Google Gemini Vision")
    print("="*60)
    
    provider = VisionProvider(
        provider="google",
        model="gemini-2.0-flash-exp"
    )
    
    result = provider.analyze_image(
        image_path="chart.png",
        prompt="分析这张图表，总结主要趋势和关键数据点",
        temperature=0.3  # 更低的温度以获得更精确的分析
    )
    
    if result["success"]:
        print(f"✓ 图表分析完成")
        print(f"{result['content']}")


def example_6_batch_processing():
    """示例 6: 批量处理图片"""
    print("\n" + "="*60)
    print("示例 6: 批量处理文件夹中的图片")
    print("="*60)
    
    provider = VisionProvider(provider="openai")
    
    results = provider.batch_analyze(
        image_dir="./images",
        prompt="识别图片中的主要物体",
        max_concurrent=3
    )
    
    print(f"✓ 批量处理完成，共处理 {len(results)} 张图片\n")
    
    for i, result in enumerate(results, 1):
        if result["success"]:
            print(f"{i}. {result['image_path']}")
            print(f"   内容: {result['content'][:100]}...")
        else:
            print(f"{i}. {result['image_path']} - 失败: {result['error']}")


def example_7_from_config():
    """示例 7: 从配置文件加载"""
    print("\n" + "="*60)
    print("示例 7: 从配置文件加载设置")
    print("="*60)
    
    provider = VisionProvider.from_config("config.yaml")
    
    result = provider.analyze_image(
        image_path="test.jpg",
        prompt="描述这张图片"
    )
    
    if result["success"]:
        print(f"✓ 使用配置文件成功")
        print(f"提供商: {result['metadata']['provider']}")
        print(f"模型: {result['model']}")


def example_8_visual_qa():
    """示例 8: 视觉问答"""
    print("\n" + "="*60)
    print("示例 8: 视觉问答 - 基于图片回答具体问题")
    print("="*60)
    
    provider = VisionProvider(provider="openai")
    
    questions = [
        "图片中有几个人？",
        "他们在做什么？",
        "场景是在室内还是室外？",
        "图片的主色调是什么？"
    ]
    
    for question in questions:
        result = provider.analyze_image(
            image_path="scene.jpg",
            prompt=question,
            max_tokens=100
        )
        
        if result["success"]:
            print(f"\nQ: {question}")
            print(f"A: {result['content']}")


def example_9_custom_parameters():
    """示例 9: 自定义参数"""
    print("\n" + "="*60)
    print("示例 9: 使用自定义参数")
    print("="*60)
    
    provider = VisionProvider(
        provider="openai",
        model="gpt-4o"
    )
    
    # 创意描述（高温度）
    result_creative = provider.analyze_image(
        image_path="art.jpg",
        prompt="用富有创意和诗意的语言描述这幅艺术作品",
        temperature=1.0,
        max_tokens=500
    )
    
    # 精确分析（低温度）
    result_precise = provider.analyze_image(
        image_path="technical_diagram.png",
        prompt="精确描述这个技术图表的结构和组件",
        temperature=0.2,
        max_tokens=1000
    )
    
    if result_creative["success"] and result_precise["success"]:
        print("✓ 不同风格的描述生成成功")
        print(f"\n创意描述:\n{result_creative['content']}")
        print(f"\n精确分析:\n{result_precise['content']}")


def example_10_error_handling():
    """示例 10: 错误处理"""
    print("\n" + "="*60)
    print("示例 10: 错误处理和重试逻辑")
    print("="*60)
    
    provider = VisionProvider(provider="openai")
    
    # 尝试分析不存在的文件
    result = provider.analyze_image(
        image_path="nonexistent.jpg",
        prompt="描述图片"
    )
    
    if not result["success"]:
        print(f"✓ 错误被正确捕获: {result['error']}")
    
    # 实现重试逻辑
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = provider.analyze_image(
                image_path="test.jpg",
                prompt="描述图片"
            )
            if result["success"]:
                print(f"✓ 第 {attempt + 1} 次尝试成功")
                break
        except Exception as e:
            print(f"第 {attempt + 1} 次尝试失败: {e}")
            if attempt == max_retries - 1:
                print("达到最大重试次数")


def main():
    """运行所有示例"""
    print("\n" + "="*60)
    print("Vision Provider 使用示例")
    print("="*60)
    
    examples = [
        ("基本使用", example_1_basic_usage),
        ("分析多张图片", example_2_multiple_images),
        ("URL 图片", example_3_url_image),
        ("Anthropic Claude", example_4_anthropic),
        ("Google Gemini", example_5_google_gemini),
        ("批量处理", example_6_batch_processing),
        ("配置文件", example_7_from_config),
        ("视觉问答", example_8_visual_qa),
        ("自定义参数", example_9_custom_parameters),
        ("错误处理", example_10_error_handling),
    ]
    
    print("\n可用示例:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")
    
    print("\n提示: 运行前请设置相应的环境变量:")
    print("  export OPENAI_API_KEY='your-key'")
    print("  export ANTHROPIC_API_KEY='your-key'")
    print("  export GOOGLE_API_KEY='your-key'")
    
    # 取消注释以运行特定示例
    # example_1_basic_usage()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
PWA 아이콘 생성 스크립트
SVG를 다양한 크기의 PNG로 변환합니다.

필요 패키지: pip install cairosvg pillow
"""

import os
import sys

# 생성할 아이콘 크기
ICON_SIZES = [16, 32, 72, 96, 128, 144, 152, 192, 384, 512]

def generate_with_cairosvg():
    """cairosvg를 사용하여 PNG 생성"""
    try:
        import cairosvg
        print("cairosvg로 아이콘 생성 중...")

        svg_path = os.path.join(os.path.dirname(__file__), 'icon.svg')

        for size in ICON_SIZES:
            output_path = os.path.join(os.path.dirname(__file__), f'icon-{size}x{size}.png')
            cairosvg.svg2png(
                url=svg_path,
                write_to=output_path,
                output_width=size,
                output_height=size
            )
            print(f"  생성됨: icon-{size}x{size}.png")

        return True
    except ImportError:
        return False

def generate_with_pillow():
    """Pillow를 사용하여 간단한 PNG 생성 (SVG 미지원, 대체용)"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        print("Pillow로 아이콘 생성 중... (단순화된 버전)")

        for size in ICON_SIZES:
            # 배경색
            img = Image.new('RGBA', (size, size), (26, 26, 46, 255))
            draw = ImageDraw.Draw(img)

            # 둥근 모서리 효과 (간단히)
            radius = size // 6

            # 채팅 버블 (분홍색)
            bubble_margin = size // 8
            bubble_height = size // 2
            draw.rounded_rectangle(
                [bubble_margin, bubble_margin, size - bubble_margin, bubble_margin + bubble_height],
                radius=radius // 2,
                fill=(233, 69, 96, 230)
            )

            # C 글자
            try:
                font_size = size // 3
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()

            text = "C"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (size - text_width) // 2
            text_y = bubble_margin + (bubble_height - text_height) // 2 - size // 20
            draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)

            # 작은 버블 (파란색)
            small_margin = size // 4
            small_top = bubble_margin + bubble_height + size // 20
            draw.rounded_rectangle(
                [small_margin, small_top, size - bubble_margin, size - bubble_margin],
                radius=radius // 3,
                fill=(15, 52, 96, 230)
            )

            # 점 3개
            dot_y = small_top + (size - bubble_margin - small_top) // 2
            dot_size = size // 30
            for i, opacity in enumerate([255, 180, 100]):
                dot_x = small_margin + size // 6 + i * (size // 8)
                draw.ellipse(
                    [dot_x - dot_size, dot_y - dot_size, dot_x + dot_size, dot_y + dot_size],
                    fill=(74, 222, 128, opacity)
                )

            output_path = os.path.join(os.path.dirname(__file__), f'icon-{size}x{size}.png')
            img.save(output_path, 'PNG')
            print(f"  생성됨: icon-{size}x{size}.png")

        return True
    except ImportError:
        return False

def main():
    print("Chat Socket PWA 아이콘 생성기")
    print("=" * 40)

    # cairosvg 시도
    if generate_with_cairosvg():
        print("\n완료! cairosvg로 아이콘이 생성되었습니다.")
        return

    # Pillow 시도
    if generate_with_pillow():
        print("\n완료! Pillow로 아이콘이 생성되었습니다.")
        print("(참고: SVG 원본과 약간 다를 수 있습니다)")
        return

    # 둘 다 실패
    print("\n오류: 아이콘 생성에 필요한 패키지가 없습니다.")
    print("다음 중 하나를 설치하세요:")
    print("  pip install cairosvg   (권장, SVG 정확히 변환)")
    print("  pip install pillow     (대체, 단순화된 버전)")
    sys.exit(1)

if __name__ == '__main__':
    main()

# intro_screen.py
import pygame
import time

# 開場像素蛇圖案（使用等寬字型會最漂亮）
PIXEL_SNAKE = [
    "   ███████████",
    "  █           █",
    " █             █",
    " █   █   █      █",
    "█    █   █      █",
    "█                █",
    "█   █ █           █",
    "█    █     █      █",
    "█████ █████      █          ███████         █████",
    " █   █     █    █          █       █       █     █",
    "  █████████     █         █         █     █       █",
    "  █       █     █         █          █    █        █      ███",
    " █        █     █        █            █  █    ████  █    █  █",
    "█ █████████     █████████      █████   ██    █    █  ████   █",
    "  ██       █                  █     █       █      █",
    "   █        █                █   ██  █     █   ██   █   ███",
    "    █████████████████████████   █  █████   █  █   █   █",
    "     █                         █   █         █    █   ███",
    "      ███████████████████████     █████████      ████",
]

# -----------------------------------------------------
# 在 Pygame 視窗中播放開場畫面
# -----------------------------------------------------
def show_intro(screen, font):
    screen.fill((30, 30, 30))
    pygame.display.set_caption("Snake Game – Intro")

    # 顯示每一行字的動畫效果
    delay = 0.1  # 秒
    for i, line in enumerate(PIXEL_SNAKE):
        label = font.render(line, True, (255, 255, 255))
        screen.blit(label, (50, 50 + i * 20))
        pygame.display.flip()
        time.sleep(delay)

    time.sleep(1.5)  # 等待 1.5 秒後清除
    screen.fill((30, 30, 30))
    pygame.display.flip()


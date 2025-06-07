from snake_game import SnakeGame
import pygame, sys

def show_cover():
    pygame.init()
    screen = pygame.display.set_mode((750, 800))
    pygame.display.set_caption("🐍 Snake Game – Start Menu")
    font_big = pygame.font.SysFont("consolas", 40)
    font_mid = pygame.font.SysFont("consolas", 26)
    font_small = pygame.font.SysFont("consolas", 20)

    C_BG = (20, 20, 20)
    C_TITLE = (255, 255, 255)
    C_MENU = (180, 180, 180)
    C_HINT = (100, 100, 100)

    title = font_big.render("🐍 Snake Game – Plus Mode", True, C_TITLE)
    start_msg = font_mid.render("Press ENTER to Start", True, C_MENU)
    leaderboard_msg = font_mid.render("Press L to View Leaderboard", True, C_MENU)
    exit_msg = font_small.render("Press ESC to Exit", True, C_HINT)

    while True:
        screen.fill(C_BG)
        screen.blit(title, ((750 - title.get_width()) // 2, 200))
        screen.blit(start_msg, ((750 - start_msg.get_width()) // 2, 320))
        screen.blit(leaderboard_msg, ((750 - leaderboard_msg.get_width()) // 2, 370))
        screen.blit(exit_msg, ((750 - exit_msg.get_width()) // 2, 500))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    pygame.quit()
                    game = SnakeGame()
                    game.run()
                elif event.key == pygame.K_l:
                    game = SnakeGame()
                    game.show_leaderboard()
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

if __name__ == "__main__":
    show_cover()

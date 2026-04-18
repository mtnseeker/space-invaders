import pygame
pygame.init()
pygame.joystick.init()
screen = pygame.display.set_mode((400, 200))
print(f"Joysticks detected: {pygame.joystick.get_count()}")
for i in range(pygame.joystick.get_count()):
    js = pygame.joystick.Joystick(i)
    js.init()
    print(f"  {i}: {js.get_name()}")
print("Press keys / buttons, Esc to quit")
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            print(f"KEY: {pygame.key.name(event.key)}")
            if event.key == pygame.K_ESCAPE: running = False
        if event.type == pygame.JOYBUTTONDOWN:
            print(f"JOY BUTTON: {event.button}")
        if event.type == pygame.JOYAXISMOTION and abs(event.value) > 0.5:
            print(f"JOY AXIS {event.axis}: {event.value:.2f}")
pygame.quit()

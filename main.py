#!/usr/bin/env python3
# BLAME: a game of visual hacking, pivoting though networks and stealing data

# Imports
import os
import sys
import time
import random
import pygame
import yaml
# Initialize pygame
pygame.init()

# Set up the window (with a funny caption)
WIDTH = 1080
HEIGHT = 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("BLAME: " + random.choice(["Insecurity is our policy.", "We're not responsible for your data.", "Data breach? What data breach?", "Everything is fine.", "I'm pretty sure that data is right in the open."]))
icon = pygame.image.load("favicon.png")
pygame.display.set_icon(icon)
# Set up the clock
clock = pygame.time.Clock()

# Set up the colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
TERMINAL_GREEN = (0, 255, 0)
COMPROMISED_RED = (255, 0, 0)

# Set up the pivot offset
pivot_offset = (0,0)

# Set up the fonts
font = pygame.font.SysFont("monospace", 15)

# Utility functions

def generate_ip():
    ip = ""
    for i in range(4):
        ip += str(random.randint(0, 255))
        if i < 3:
            ip += "."
    return ip

def generate_name():
    name = ""
    toptier = ["Corperate Server", "Bare Metal Server"]
    suffixes = ["Computer", "PC", "Raspberry Pi", "Workstation", "Laptop", "Phone", "Tablet", "Fridge", "Battlestation"]
    users = ["Alice's", "Bob's", "Carol's", "Dave's", "Eve's", "Frank's", "Grace's", "Heidi's", "Ivan's", "Judy's", "Mallory's", "Oscar's", "Peggy's", "Sybil's", "Trudy's", "Victor's", "Walter's"]
    if random.randint(0, 1) == 0:
        name += random.choice(users) + " " + random.choice(suffixes)
    else:
        name += random.choice(toptier)
    
    return name

def pivot(coords):
    return (coords[0] + pivot_offset[0], coords[1] + pivot_offset[1])

def px(x):
    return x + pivot_offset[0]

def py(y):
    return y + pivot_offset[1]

def generate_junk_text(length):
    junk = ""
    for i in range(length):
        junk += random.choice(["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"])
    return junk

def draw_arrow(
        surface: pygame.Surface,
        start: pygame.Vector2,
        end: pygame.Vector2,
        color: pygame.Color,
        body_width: int = 2,
        head_width: int = 4,
        head_height: int = 2,
    ):
    """Draw an arrow between start and end with the arrow head at the end.

    Args:
        surface (pygame.Surface): The surface to draw on
        start (pygame.Vector2): Start position
        end (pygame.Vector2): End position
        color (pygame.Color): Color of the arrow
        body_width (int, optional): Defaults to 2.
        head_width (int, optional): Defaults to 4.
        head_height (float, optional): Defaults to 2.
    """
    arrow = start - end
    angle = arrow.angle_to(pygame.Vector2(0, -1))
    body_length = arrow.length() - head_height

    # Create the triangle head around the origin
    head_verts = [
        pygame.Vector2(0, head_height / 2),  # Center
        pygame.Vector2(head_width / 2, -head_height / 2),  # Bottomright
        pygame.Vector2(-head_width / 2, -head_height / 2),  # Bottomleft
    ]
    # Rotate and translate the head into place
    translation = pygame.Vector2(0, arrow.length() - (head_height / 2)).rotate(-angle)
    for i in range(len(head_verts)):
        head_verts[i].rotate_ip(-angle)
        head_verts[i] += translation
        head_verts[i] += start

    pygame.draw.polygon(surface, color, head_verts)

    # Stop weird shapes when the arrow is shorter than arrow head
    if arrow.length() >= head_height:
        # Calculate the body rect, rotate and translate into place
        body_verts = [
            pygame.Vector2(-body_width / 2, body_length / 2),  # Topleft
            pygame.Vector2(body_width / 2, body_length / 2),  # Topright
            pygame.Vector2(body_width / 2, -body_length / 2),  # Bottomright
            pygame.Vector2(-body_width / 2, -body_length / 2),  # Bottomleft
        ]
        translation = pygame.Vector2(0, body_length / 2).rotate(-angle)
        for i in range(len(body_verts)):
            body_verts[i].rotate_ip(-angle)
            body_verts[i] += translation
            body_verts[i] += start

        pygame.draw.polygon(surface, color, body_verts)
    

loglines = []
loglimit = 10
def log(text): # top left corner
    global loglines
    loglines.append(text)
    if len(loglines) > loglimit:
        loglines = loglines[1:]

# Classes

class InputBox():
    def __init__(self, x, y, width, height, text):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.focus = False
        self.box = None
        self.parseCommand = None
        
    def draw(self):
        self.box = pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, WHITE, (self.x + 1, self.y + 1, self.width - 2, self.height - 2))
        text = font.render("$ " + self.text, 1, BLACK)
        screen.blit(text, (self.x + 5, self.y + 5))

    def update(self, key, event):
        if self.focus:   
            if key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif key == pygame.K_RETURN:
                if self.parseCommand != None:
                    self.parseCommand(self.text)
                self.text = ""
            else:
                self.text += event.unicode

# put an input box bottom left of the screen
inputbox = InputBox(5, HEIGHT - 25, 200, 20, "")

class Computer():
    def __init__(self, x, y, linked_computers, opts=None, player=None):
        self.player = player
        self.x = x
        self.y = y
        self.width = 200
        self.height = 100
        self.color = WHITE
        self.ip = generate_ip()
        self.name = generate_name()
        self.font = pygame.font.SysFont("monospace", 15)
        self.security = random.randint(0, 100)
        self.compromised = False
        self.linked_computers = linked_computers
        self.visible = False
        self.hackbutton = None
        self.scanbutton = None
        self.siphonbutton = None
        self.disconnectbutton = None
        self.drawn = False
        self.box = None
        self.bufsploit_animation = False
        self.flags = []
        self.dialogue = []
        self.password = None
        self.money = 0
        if opts != None:
            if "name" in opts:
                self.name = opts["name"]
            if "ip" in opts:
                self.ip = opts["ip"]
            if "security" in opts:
                self.security = opts["security"]
            if "password" in opts:
                self.password = opts["password"]
                p = self.password 
            if "visible" in opts:
                self.visible = opts["visible"]
            if "flags" in opts:
                self.flags = opts["flags"]
            if "dialogue" in opts:
                self.dialogue = opts["dialogue"]
            if "links" in opts:
                for name in opts["links"]:
                    link = opts["links"][name]
                    self.linked_computers.append(Computer(link["x"], link["y"], [], opts=link, player=player))
            if "money" in opts:
                self.money = opts["money"]
        self.width += len(self.name)*2
        if self.password == None:
            if self.security < 10:
                self.password = "password"
            elif self.security < 25:
                self.password = "123456"
            elif self.security < 50:
                self.password = "password123*"
            elif self.security < 99:
                self.password = random.choice(["password", "123456", "password123*", "password123", "123456789", "qwerty", "12345678", "111111", "1234567890", "1234567", "password1", "12345", "123123", "987654321", "qwertyuiop", "mynoob", "123321", "666666", "18atcskd2w", "7777777", "1q2w3e4r", "654321", "555555", "3rjs1la7qe", "google", "1q2w3e4r5t", "123qwe", "zxcvbnm", "1q2w3e"])
            else:
                self.password = None # None denotes that the computer has no entrypoint. This is a computer that is running a top tier defense system, such as a airgapped server or a computer with no network card.
        self.dragging = False
        self.dragx = 0
        self.dragy = 0
        self.dialogue_text = None
        self.dialogue_hide = None



    def scan_network(self):
        for computer in self.linked_computers:
            computer.visible = True
    
    def draw(self):
        for d in self.dialogue:
            dialogue = self.dialogue[d]
            wait = lambda: False
            if dialogue["await"] == "compromise":
                wait = lambda: self.compromised
            self.speak(dialogue["text"], wait)
        if self.bufsploit_animation:
            self.bufsploit_anim_draw()
            self.drawn = False
            return
        if self.compromised:
            self.color = COMPROMISED_RED
        else:
            self.color = WHITE
        for computer in self.linked_computers:
            if computer == self:
                continue
            if computer.visible:
                if computer != player:
                    pygame.draw.line(screen, TERMINAL_GREEN, (px(self.x) + 100, py(self.y) + 50), (px(computer.x) + 100, py(computer.y) + 50), 2)
                    computer.draw()
        self.box = pygame.draw.rect(screen, self.color, (px(self.x), py(self.y), self.width, self.height))
        pygame.draw.rect(screen, BLACK, (px(self.x) + 1, py(self.y)+ 1, self.width - 2, self.height - 2))
        ip_text = self.font.render(self.ip, 1, WHITE)
        name_text = self.font.render(self.name, 1, WHITE)
        screen.blit(ip_text, (px(self.x) + 5, py( self.y) + 5))
        screen.blit(name_text, (px(self.x) + 5, py( self.y) + 25))
        if self.password == None:
            password_text = self.font.render("No entrypoint", 1, COMPROMISED_RED)
            screen.blit(password_text, (px(self.x) + 5, py(self.y) + 45))
        # scanbutton is bottom right corner (only appears if machine comprimised)
        if self.compromised:
            self.scanbutton = pygame.draw.rect(screen, TERMINAL_GREEN, (px(self.x) + self.width - 55, py(self.y) + self.height - 20, 15, 15))
            scan_text = self.font.render("Scan", 1, WHITE)
            screen.blit(scan_text, (px(self.x) + self.width - 40, py(self.y) + self.height - 20))

            # Siphon button is bottom left corner if machine comprimised
            self.siphonbutton = pygame.draw.rect(screen, TERMINAL_GREEN, (px(self.x) + 5, py(self.y) + self.height - 20, 15, 15))
            siphon_text = self.font.render("Siphon $" + str(self.money), 1, WHITE)
            screen.blit(siphon_text, (px(self.x) + 25, py(self.y) + self.height - 20))
            self.disconnectbutton = pygame.draw.rect(screen, COMPROMISED_RED, (px(self.x) + self.width - 20, py(self.y) + 5, 15, 15))
            disconnect_text = self.font.render("X", 1, WHITE)
            screen.blit(disconnect_text, (px(self.x) + self.width - 15, py(self.y) + 5))


        # hackbutton is bottom left corner
        if not self.compromised and self.password != None:
            self.hackbutton = pygame.draw.rect(screen, TERMINAL_GREEN, (px(self.x) + 5, py(self.y) + self.height - 20, 15, 15))
            hack_text = self.font.render("Hack", 1, WHITE)
            screen.blit(hack_text, (px(self.x) + 25, py(self.y) + self.height - 20))
            #disconnectbutton is top right corner
        if self.dialogue_text != None:
            if not self.dialogue_hide():
                # render an arrow and point it at the box, then render the text
                o = 0
                draw_arrow(screen, pygame.Vector2(px(self.x), py(self.y) -50), pygame.Vector2(px(self.x), py(self.y)), TERMINAL_GREEN, head_width=10, head_height=5)
                for line in self.dialogue_text.split("\n"):
                    text = font.render(line, 1, TERMINAL_GREEN)
                    screen.blit(text, (px(self.x) + 5, py(self.y) - 45 + o))
                    o += 15
        self.drawn = True
        last_drawn_computers.append(self)
    
    def speak(self, text, hide_lambda): # point an arrow at the computer and display text, this is used for the tutorial.
        self.dialogue_text = text
        self.dialogue_hide = hide_lambda
        
    
    def disconnect(self):
        if not "nodisconnect" in self.flags:
            self.visible = False

    def bufsploit_anim_draw(self):
        # basically its a bunch of text that floods out of the box but with a typewriter effect
        # first, draw the box
        pygame.draw.rect(screen, self.color, (px(self.x), py(self.y), self.width, self.height))
        pygame.draw.rect(screen, BLACK, (px(self.x) + 1, py(self.y)+ 1, self.width - 2, self.height - 2))
        # then, draw the text
        junk = generate_junk_text(100)
        offset = 0
        for i in range(100):
            text = font.render(junk[:i], 1, WHITE)
            screen.blit(text, (px(self.x) + 5, py(self.y) + 5))
            offset += 15
            if offset > 100:
                offset = 0
            time.sleep(0.01)
        self.compromised = True
        self.bufsploit_animation = False

    
    def button_pressed(self, x, y, event=None):
        if self.drawn:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.compromised:
                    if not self.scanbutton == None:
                        if self.scanbutton.collidepoint(x, y):
                            self.scan_network()
                    if not self.siphonbutton == None:
                        if self.siphonbutton.collidepoint(x, y):
                            self.player.money += self.money
                            self.money = 0
                    if not self.disconnectbutton == None:
                        if self.disconnectbutton.collidepoint(x, y):
                            self.disconnect()
                else:
                    if not self.hackbutton == None:
                        if self.hackbutton.collidepoint(x, y):
                            password = inputbox.text
                            ret = self.hack(password)
                            if ret:
                                inputbox.text = ""
                            else:
                                inputbox.text = password
                    if not self.disconnectbutton == None:
                        if self.disconnectbutton.collidepoint(x, y):
                            self.disconnect()
            if event != None:
                if self.drawn:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if self.box.collidepoint(x, y):
                            self.dragging = True
                            self.dragx, self.dragy = px(x), py(y)
                    if event.type == pygame.MOUSEBUTTONUP:
                        self.dragging = False
                    if event.type == pygame.MOUSEMOTION:
                        pygame.draw.rect(screen, self.color, (px(self.x), py(self.y), 5, 5))
                        if self.dragging:
                            self.x += px(x) - self.dragx
                            self.y += py(y) - self.dragy
                            self.dragx, self.dragy = px(x), py(y)
    def hack(self, pwd):
        if pwd == "bufsploit":
            if self.player.programs["bufsploit"] > 0:
                self.bufsploit_animation = True
                # self.generate_trail()
                self.player.programs["bufsploit"] -= 1
                return True
        if self.password == None:
            return False
        if pwd == self.password:
            self.compromised = True
            player.hacks += 1
            # self.generate_trail()
            return True
        else:
            return False
    

class Network():
    def __init__(self):
        self.computers = None
        self.compromised = False

    def draw(self):
        for computer in self.computers:
            if computer.visible:
                computer.draw()
    
    def hack(ip,pwd):
        for computer in self.computers:
            if computer.ip == ip:
                return computer.hack(pwd)
        return False
        
    def compromise(self):
        for computer in self.computers:
            if not computer.compromised:
                return False
        self.compromised = True
        return True
    
    def link_computer(self, computer):
        #computer.linked_computers = self.computers
        self.computers.append(computer)

    
    def get_computer(self, ip):
        for computer in self.computers:
            if computer.ip == ip:
                return computer
        return None

class Player(Computer):
    def __init__(self, x, y):
        super().__init__(x, y, None)
        self.visible = True
        self.color = TERMINAL_GREEN
        self.password = None
        self.ip = "127.0.0.1"
        if sys.platform == "win32":
            self.name = os.getlogin()
        elif sys.platform == "emscripten":
            self.name = "Hacker"
        elif sys.platform == "darwin":
            self.name = "/Users/" + os.environ["USER"]
        elif sys.platform == "linux":
            self.name = "/home/" + os.environ["USER"]
        self.security = 100
        self.compromised = False
        self.font = pygame.font.SysFont("monospace", 15)
        self.linked_computers = []
        self.visible = True
        self.known_ips = []
        self.programs = {
            "bufsploit": 0,
            "tcpripper": 0,
        }
        self.money = 0
        self.hacks = 0
        self.opts = []

    def draw(self):
        for computer in self.linked_computers:
            if computer.visible:
                pygame.draw.line(screen, TERMINAL_GREEN, (px(self.x) + 100, py(self.y) + 50), (px(computer.x) + 100, py(computer.y) + 50), 2)
                computer.draw()
        pygame.draw.rect(screen, self.color, (px(self.x), py(self.y), self.width, self.height))
        pygame.draw.rect(screen, BLACK, (px(self.x) + 1, py(self.y) + 1, self.width - 2, self.height - 2))
        ip_text = self.font.render(self.ip, 1, TERMINAL_GREEN)
        name_text = self.font.render(self.name, 1, TERMINAL_GREEN)
        hacks_text = self.font.render("Hacks: " + str(self.hacks), 1, TERMINAL_GREEN)
        balance_text = self.font.render("$" + str(self.money), 1, TERMINAL_GREEN) # top right corner
        o = len(str(self.money))+1
        o = o*15
        screen.blit(balance_text, (px(self.x) + self.width-o, py(self.y) + 5))
        if not self.programs["bufsploit"] == 0:
            bufsploit_text = self.font.render("bufsploit: " + str(self.programs["bufsploit"]), 1, TERMINAL_GREEN)
            screen.blit(bufsploit_text, (px(self.x) + 5, py(self.y) + 65))
        if not self.programs["tcpripper"] == 0:
            tcpripper_text = self.font.render("tcpripper: " + str(self.programs["tcpripper"]), 1, TERMINAL_GREEN)
            screen.blit(tcpripper_text, (px(self.x) + 5, py(self.y) + 85))
        screen.blit(hacks_text, (px(self.x) + 5, py(self.y) + 45))
        screen.blit(ip_text, (px(self.x) + 5, py(self.y) + 5))
        screen.blit(name_text, (px(self.x ) + 5, py(self.y) + 25))


    def button_pressed(self, x, y, event=None):
        if event != None:
            if self.drawn:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.box.collidepoint(x, y):
                        self.dragging = True
                        self.dragx, self.dragy = x, y
                if event.type == pygame.MOUSEBUTTONUP:
                    self.dragging = False
                if event.type == pygame.MOUSEMOTION:
                    if self.dragging:
                        self.x += x - self.dragx
                        self.y += y - self.dragy
                        self.dragx, self.dragy = x, y
# Set up the game
player = Player(WIDTH/2-100, HEIGHT/2-50)

computers = []
gamedata = yaml.load(open("gamedata.yml", "r"), Loader=yaml.FullLoader)
progression = gamedata["network"]
for name in progression:
    computer = progression[name]
    computers.append(Computer(computer["x"], computer["y"], [], opts=computer, player=player))
# computer1 = Computer(100, 100, [player])
# computer1.visible = True
# computer1.password = "tutorial"
# computer1.name = "Dad's Office Computer"
# computer1.dialogue("This is your father's office computer.\nIt is running a vulnerable version of Windows XP.\nTry to hack it with the password 'tutorial'.", lambda: computer1.compromised)
prices = {
    "bufsploit": 100,
    "tcpripper": 250
}
def parse_command(cmd):
    args = cmd.split(" ")
    if cmd == "sv_cheats 1":
        player.programs["bufsploit"] = 9999999
        player.programs["tcpripper"] = 9999999
        player.hacks = 9999999
        player.money = 9999999
        log("Cheats enabled.")
    if args[0] == "shop":
        if len(args) == 1:
            log("Available programs:")
            log("bufsploit - $" + str(prices["bufsploit"]))
            log("tcpripper - $" + str(prices["tcpripper"]))
        else:
            if args[1] == "bufsploit":
                if player.money >= prices["bufsploit"]:
                    player.money -= prices["bufsploit"]
                    player.programs["bufsploit"] += 1
                    log("bufsploit purchased.")
                else:
                    log("Not enough money.")
            elif args[1] == "tcpripper":
                if player.money >= prices["tcpripper"]:
                    player.money -= prices["tcpripper"]
                    player.programs["tcpripper"] += 1
                    log("tcpripper purchased.")
                else:
                    log("Not enough money.")


player.linked_computers = [computers[0]]

inputbox.parseCommand = parse_command

# Main game loop
running = True
shift_held = False
shift_coords = None
last_drawn_computers = []
while running:
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            inputbox.update(event.key, event)
            if event.key == pygame.K_LSHIFT:
                shift_held = True
                shift_coords = pygame.mouse.get_pos()
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_LSHIFT:
                shift_held = False
                shift_coords = None
        if event.type == pygame.MOUSEMOTION:
            if shift_held:
                pivot_offset = (pivot_offset[0] + (pygame.mouse.get_pos()[0] - shift_coords[0]), pivot_offset[1] + (pygame.mouse.get_pos()[1] - shift_coords[1]))
                shift_coords = pygame.mouse.get_pos()
        if inputbox.box != None:
            if not inputbox.box.collidepoint(pygame.mouse.get_pos()):
                inputbox.focus = False
            else:
                inputbox.focus = True
        x, y = pygame.mouse.get_pos()
        player.button_pressed(x, y)
        for computer in last_drawn_computers:
            if computer.visible:
                if computer.drawn:
                    computer.button_pressed(x, y, event=event)
    screen.fill(BLACK)
    
    # top right corner small red box with X in it
    # x = pygame.draw.rect(screen, COMPROMISED_RED, (WIDTH - 20, 0, 20, 20))
    # pygame.draw.line(screen, BLACK, (WIDTH - 20, 0), (WIDTH, 20), 2)
    # pygame.draw.line(screen, BLACK, (WIDTH - 20, 20), (WIDTH, 0), 2)
    player.draw()
    inputbox.draw()
    for i in range(len(loglines)):
        text = font.render(loglines[i], 1, TERMINAL_GREEN)
        screen.blit(text, (5, 5 + i*15))
    # Draw the screen
    pygame.display.flip()
    clock.tick(60)
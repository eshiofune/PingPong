from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty,\
    ObjectProperty, BooleanProperty, StringProperty
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.base import runTouchApp
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.network.urlrequest import UrlRequest
from collections import OrderedDict
#from kivymd.button import MDFlatButton
#from kivymd.theming import ThemeManager
import json


class PongPaddle(Widget):
    speed = NumericProperty(75)
    score = NumericProperty(0)
    
    def move_up(self):
        self.center_y += self.speed

    def move_down(self):
        self.center_y -= self.speed

    def bounce_ball(self, ball):
        if self.collide_widget(ball):
            vx, vy = ball.velocity
            offset = (ball.center_y - self.center_y) / (self.height / 2)
            bounced = Vector(-1 * vx, vy)
            if abs(bounced[0]) <= 25:
                vel = bounced * 1.1
            else:
                vel = bounced
            ball.velocity = vel.x, vel.y + offset

class AIPlayer(PongPaddle):
    vision = NumericProperty(0)
    vision_range = NumericProperty(1)

    def __init__(self, difficulty, position, *args, **kwargs):
        super(AIPlayer, self).__init__(**kwargs)
        if difficulty == 'easy':
            self.speed = 5
            self.vision_range = 4
        elif difficulty == 'moderate':
            self.speed = 10
            self.vision_range = 3
        elif difficulty == 'hard':
            self.speed = 30
            self.vision_range = 2
        elif difficulty == 'insane':
            self.speed = 40
            self.vision_range = 1
        if position == 'left':
            pass
        elif position == 'right':
            self.x = Window.width - self.width
        self.center_y = Window.center[1] * (3/2)

    def set_vision(self):
        self.vision = Window.width / self.vision_range
        
    def ball_in_vision(self, ball):
        if ball.pos[0] - self.size[0] <= self.vision:
            return True
        else:
            return False

    def intercept_ball(self, ball):
        #if ball pos not between two edges of paddle : move
        if self.ball_in_vision(ball):
            #if ball pos < bottom:
            if ball.pos[1] < self.pos[1]:            
                self.move_down()
            #else if ball pos > top:
            elif ball.pos[1] > (self.pos[1] + self.size[1]):            
                self.move_up()


class PongBall(Widget):
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    velocity = ReferenceListProperty(velocity_x, velocity_y)

    def move(self):
        self.pos = Vector(*self.velocity) + self.pos


class PongGame(Widget):
    pause = BooleanProperty(False)
    end_game = BooleanProperty(False)
    ball = ObjectProperty(None)
    player1 = ObjectProperty(None)
    player2 = ObjectProperty(None)
    left_label = ObjectProperty(None)
    right_label = ObjectProperty(None)
    
    def __init__(self, difficulty, num_players, **kwargs):
        super(PongGame, self).__init__(**kwargs)
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        
    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'w':
            self.player1.move_up()
        elif keycode[1] == 's':
            self.player1.move_down()
        elif keycode[1] == 'numpadadd':
            self.player2.move_up()
        elif keycode[1] == 'numpadenter':
            self.player2.move_down()
        elif keycode[1] == 'spacebar':
            self.pause = not self.pause
            self.parent.manager.current = 'main_screen'

    def serve_ball(self, factor = 1):
        self.ball.center = self.center
        self.ball.velocity = Vector(self.vel) * factor

    def update(self, dt):
        if self.pause or self.end_game:
            return
        if 'AIPlayer' in str(self.player1.__class__):
            if self.player1.vision != Window.width / self.player1.vision_range:
                self.player1.set_vision()
            self.player1.intercept_ball(self.ball)        
        if 'AIPlayer' in str(self.player2.__class__):
            if self.player2.vision != Window.width / self.player2.vision_range:
                self.player2.set_vision()
            self.player2.intercept_ball(self.ball)
        self.ball.move()
        #Bounce off paddles
        self.player1.bounce_ball(self.ball)
        self.player2.bounce_ball(self.ball)        
        #Bounce ball off bottom or top
        if (self.ball.y < self.y) or (self.ball.top > self.top):
            self.ball.velocity_y *= -1
        #Went of to a side to score point
        if self.ball.x < self.x:            
            self.player2.score += 1
            self.right_label.text = str(self.player2.score)
            if self.player2.score >= \
                self.parent.manager.settings_screen.score_limit:
                    self.end_game = True
                    self.parent.manager.main_screen.active_game = False
                    self.parent.end(
                        winner = self.parent.manager.settings_screen.player2
                        )
            else:
                self.serve_ball(factor = -1)
        if self.ball.x > self.width:            
            self.player1.score += 1
            self.left_label.text = str(self.player1.score)
            if self.player1.score >= \
                self.parent.manager.settings_screen.score_limit:
                    self.end_game = True
                    self.parent.manager.main_screen.active_game = False
                    self.parent.end(
                        winner = self.parent.manager.settings_screen.player1
                        )
            else:
                self.serve_ball(factor = -1)

    def on_touch_move(self, touch):
        if touch.x < self.width / 3:
            self.player1.center_y = touch.y
        if touch.x > self.width - self.width / 3:
            self.player2.center_y = touch.y

    def clearSelf(self):
        self.parent.clear_widgets()

class ScreenManagement(ScreenManager):
    main_screen = ObjectProperty(None)
    game_screen = ObjectProperty(None)
    settings_screen = ObjectProperty(None)
    game_over_screen = ObjectProperty(None)

    def home(self, *largs):
        self.current = 'main_screen'

class MainScreen(Screen):
    active_game = BooleanProperty(False)
    
    def __init__(self, *args, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        btnTexts = OrderedDict()
        btnTexts["Start Game"] = self.start_game
        btnTexts["Resume Game"] = self.resume_game        
        btnTexts["Settings"] = self.settings
        btnTexts["Help"] = self.show_help
        
        layout = GridLayout()
        layout.rows = len(btnTexts)
        layout.cols = 3
        for btn in btnTexts:
            label = Label()
            layout.add_widget(label)
            button = Button(text = str(btn))
            button.bind(on_release = btnTexts[btn])
            layout.add_widget(button)
            label = Label()
            layout.add_widget(label)
        self.add_widget(layout)

    def start_game(self, *largs):
        self.manager.current = 'game_screen'
        self.manager.game_screen.start(active_game = self.active_game)
        self.active_game = True

    def resume_game(self, *largs):
        try:
            #Tries to access GameScreen game
            self.manager.game_screen.game.pause = \
                not self.manager.game_screen.game.pause
        except Exception:
            #Handles the case where there is no game
            print('No game to resume')
        else:
            #Goes to the game screen if a game exists
            self.manager.current = 'game_screen'
            
    def settings(self, *largs):
        self.manager.current = 'settings_screen'
        try:
            self.manager.settings_screen.read()
        except Exception:
            print('No file')

    def show_help(self, *largs):
        self.manager.current = 'help_screen'

class GameScreen(Screen):
    players = StringProperty("")
    score_limit = NumericProperty(1)
    winner = StringProperty("")
    
    def start(self, active_game):
        data = self.manager.settings_screen.read()
        num_players = data['num_of_players']
        self.score_limit = data['score_lim']
        if active_game:
            self.game.clearSelf()
        self.ai_difficulty = data['ai_difficulty']
        self.game = PongGame(self.ai_difficulty, num_players)
        if num_players == '0':
            self.game.remove_widget(self.game.player1)
            self.game.remove_widget(self.game.player2)
            self.game.player1 = self.create_ai("left")
            self.game.player2 = self.create_ai("right")
            self.game.add_widget(self.game.player1)
            self.game.add_widget(self.game.player2)
        elif num_players == '1':
            self.game.remove_widget(self.game.player1)
            self.game.player1 = self.create_ai("left")
            self.game.add_widget(self.game.player1)
        elif num_players == '2':
            pass
        self.game.vel = self.manager.settings_screen.ball_speed_tuple
        self.add_widget(self.game)
        self.game.serve_ball()
        Clock.schedule_interval(self.game.update, 1.0 / 60.0)

    def create_ai(self, ai_position):
        player = AIPlayer(
            difficulty = self.ai_difficulty,
            position = ai_position
            )
        return player

    def end(self, winner):
        self.manager.current = 'game_over_screen'
        self.winner = winner
        self.game = None
        self.clear_widgets()


class SettingsScreen(Screen):
    #TextInputs:
    ai_difficulty = ObjectProperty(None)
    ball_speed = ObjectProperty(None)
    player_num = ObjectProperty(None)
    player_left = ObjectProperty(None)
    player_right = ObjectProperty(None)
    txt_score_limit = ObjectProperty(None)
    #Values:
    ai_difficulty_text = StringProperty("")
    num_of_players_text = StringProperty("")
    player1 = StringProperty("")
    player2 = StringProperty("")
    score_limit = NumericProperty(1)

    def __init__(self, *args, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)
        self.ball_speed_tuple = (4, 0)
        try:
            data = self.read()
            self.score_limit = int(data['score_lim'])
            players = data['players'].split('-')
            self.player1 = players[0]
            self.player2 = players[1]
            self.ai_difficulty_text = data['ai_difficulty']
            self.num_of_players_text = data['num_of_players']
            self.ball_speed_tuple = (int(data['ball_speed']), 0)
        except Exception:
            print('No file')   

    def on_enter(self):
        #If game is active, prevent user from making some changes:
        self.set_state(self.manager.main_screen.active_game)
        #Fill textinputs:
        self.player_left.text = str(self.player1)
        self.player_right.text = str(self.player2)
        self.txt_score_limit.text = str(self.score_limit)
        self.ai_difficulty.text = str(self.ai_difficulty_text)
        self.player_num.text = str(self.num_of_players_text)
        self.ball_speed.text = str(self.ball_speed_tuple[0])

    def set_state(self, boolean):
        self.ai_difficulty.disabled = boolean
        self.ball_speed.disabled = boolean
        self.player_num.disabled = boolean
        self.player_left.disabled = boolean
        self.player_right.disabled = boolean
        
    def save(self, *largs):
        #Set properties equal to textinput values:
        self.score_limit = int(self.txt_score_limit.text
                    ) if self.txt_score_limit.text.isdigit() and int(
                    self.txt_score_limit.text) > 0 else self.score_limit
        ball_speed = int(self.ball_speed.text
                    ) if self.ball_speed.text.isdigit() and int(
                    self.ball_speed.text) > 0 else 4
        self.ball_speed_tuple = (ball_speed, 0)
        self.num_of_players_text = self.player_num.text \
                    if self.player_num.text.isdigit() and int(
                    self.player_num.text) in range(0, 3) else "1"
        self.player1 = "Computer1" if self.num_of_players_text == "0" \
                    else "Computer" if self.num_of_players_text == "1" \
                    else self.player_left.text
        self.player2 = "Computer2" if self.num_of_players_text == "0" \
                    else self.player_right.text
        self.ai_difficulty_text = self.ai_difficulty.text.lower()
        #Store in file
        players = '%s-%s' % (self.player1, self.player2)
        data = {'players' : players, 'score_lim' : self.score_limit,
                'ai_difficulty' : self.ai_difficulty_text,
                'num_of_players' : self.num_of_players_text,
                'ball_speed' : ball_speed
                }   
        self.write(data)
        self.manager.current = 'main_screen'

    def write(self, data):
        with open('gamesettings.pong' , 'wb') as settingsFile:
            data = str.encode(json.dumps(data))
            settingsFile.write(data)
            settingsFile.flush()

    def read(self):    
        with open('gamesettings.pong' , 'rb') as settingsFile:
            data = settingsFile.read()
            settingsFile.flush()
            data = data.decode()
            data = json.decoder.JSONDecoder().decode(data)
            self.score_limit = data['score_lim']
        return data

    def reset(self):
        self.player_left.text = "Computer"
        self.player_right.text = "Player"
        self.txt_score_limit.text = "1"
        self.ai_difficulty.text = "Easy"
        self.player_num.text = "1"
        self.ball_speed.text = "4"


class GameOverScreen(Screen):  
    def on_enter(self):
        winner = self.manager.game_screen.winner
        layout1 = BoxLayout(orientation='vertical')
        layout1.add_widget(Label())
        label1 = Label(text = "Game over: ", size_hint = (1,1))
        label1.text += winner.strip() + " wins"
        layout1.add_widget(label1)
        layout2 = BoxLayout(orientation='horizontal')
        layout2.add_widget(Label())
        btn = Button(text = 'Home')
        btn.bind(on_release = self.manager.home)
        layout2.add_widget(btn)
        layout2.add_widget(Label())
        layout1.add_widget(layout2)
        layout1.add_widget(Label())
        self.add_widget(layout1)

    def on_leave(self):
        self.clear_widgets()


class HelpScreen(Screen):
    help_text = StringProperty("")

    def __init__(self, **kwargs):
        super(HelpScreen, self).__init__(**kwargs)
        self.help_text = '\
        Game Help: \n \
        If using a keyboard: \n \
        Left-Player: Press w to move up, s to move down \n \
        Right-Player: Press the numpad plus key to move up and the numpad \n \
                      enter key to move down \n \
        If using a touchscreen device, simply drag the paddles up or down \n \
        Press spacebar to pause the game and click Resume Game to continue \n \
        \n\n \
        Settings Help: \n \
        Initial ball speed: speed with which ball moves when \n \
                            a new game starts \n \
        Score Limit: First person to reach this score wins \n \
        Number Of Players: \n \
                           0: Computer plays against itself \n \
                           1: Computer plays as Left-Player \n \
                           2: Two human players play against each other \n \
        AI Difficulty: easy, moderate, hard or insane \n \
        '

    def home(self, *largs):
        self.manager.current = 'main_screen'


class PongApp(App):
    #theme_cls = ThemeManager()
    def build(self):        
        return ScreenManagement()


if __name__ == '__main__':
    PongApp().run()

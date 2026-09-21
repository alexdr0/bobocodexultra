"""Offline arcade rules and CLI integration; no router or network required."""

import importlib.util
import math
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bcu_games", ROOT / "bcu_games.py")
games = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = games
SPEC.loader.exec_module(games)


class SnakeTests(unittest.TestCase):
    def test_food_growth_and_wall(self):
        snake = games.Snake(12, 9)
        snake.food = (snake.body[0][0] + 1, snake.body[0][1])
        snake.step()
        self.assertEqual((snake.score, len(snake.body)), (10, 5))
        for _ in range(12):
            snake.step()
        self.assertFalse(snake.alive)

    def test_reverse_is_rejected_and_reset_restores_score(self):
        snake = games.Snake()
        snake.turn((-1, 0))
        self.assertEqual(snake.direction, (1, 0))
        snake.turn((0, -1))
        snake.turn((0, 1))
        self.assertEqual(snake.direction, (0, -1))
        snake.score = 90
        snake.reset()
        self.assertEqual(snake.score, 0)

    def test_moving_into_vacated_tail_is_safe(self):
        snake = games.Snake(9, 9)
        snake.body = [(4, 4), (4, 5), (5, 5), (5, 4)]
        snake.direction = (1, 0)
        snake.food = (0, 0)
        snake.step()
        self.assertTrue(snake.alive)
        self.assertEqual(snake.body[0], (5, 4))


class PongTests(unittest.TestCase):
    def test_player_controls_and_scoring(self):
        pong = games.Pong()
        pong.move(-100)
        self.assertEqual(pong.player, 1)
        pong.x, pong.y, pong.vx, pong.vy = pong.width - 0.1, pong.height / 2, 2, 0
        pong.ai = 1
        pong.step()
        self.assertEqual(pong.points[0], 1)
        self.assertEqual(pong.winner, None)

    def test_game_ends_at_seven_and_reset_works(self):
        pong = games.Pong()
        pong.points = [6, 0]
        pong.x, pong.y, pong.vx, pong.vy = pong.width - 0.1, pong.height / 2, 2, 0
        pong.ai = 1
        pong.step()
        self.assertEqual(pong.winner, 0)
        pong.step()
        self.assertEqual(pong.points, [7, 0])
        pong.reset()
        self.assertEqual(pong.points, [0, 0])


class DoomTests(unittest.TestCase):
    def test_maze_reachable_and_rectangular(self):
        game = games.Doom()
        self.assertEqual(len({len(row) for row in game.maze}), 1)
        pending = [(int(game.x), int(game.y))]
        reachable = set(pending)
        while pending:
            x, y = pending.pop()
            for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if neighbor not in reachable and not game.wall(*neighbor):
                    reachable.add(neighbor)
                    pending.append(neighbor)
        self.assertTrue(all((int(e.x), int(e.y)) in reachable for e in game.enemies))

    def test_raycast_shooting_and_ammo(self):
        game = games.Doom()
        self.assertTrue(math.isclose(game.ray(0)[0], 20.5))
        self.assertTrue(game.shoot())
        self.assertTrue(game.shoot())
        self.assertEqual((game.kills, game.ammo), (1, 22))
        game.ammo = 0
        self.assertFalse(game.shoot())

    def test_walls_block_movement_and_fire(self):
        game = games.Doom()
        game.x, game.y = 1.25, 1.5
        game.angle = math.pi
        game.move(0.5, 0)
        self.assertEqual(game.x, 1.25)
        game.x, game.y, game.angle = 2.5, 3.5, -math.pi / 2
        self.assertFalse(game.visible(game.enemies[0]))


class CLITests(unittest.TestCase):
    def test_game_help_and_noninteractive_error(self):
        for name in ("snake", "pong", "doom"):
            with self.subTest(name=name):
                help_result = subprocess.run([sys.executable, str(ROOT / "openrouter-codex"), name, "--help"],
                                             text=True, capture_output=True, check=False)
                self.assertEqual(help_result.returncode, 0, help_result.stderr)
                result = subprocess.run([sys.executable, str(ROOT / "openrouter-codex"), name],
                                        text=True, capture_output=True, check=False)
                self.assertEqual(result.returncode, 1)
                self.assertIn("interactive terminal", result.stderr)

    def test_built_in_game_docs(self):
        result = subprocess.run([sys.executable, str(ROOT / "openrouter-codex"), "docs", "games"],
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(all(name in result.stdout for name in ("snake", "pong", "doom")))


if __name__ == "__main__":
    unittest.main()

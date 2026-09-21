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
        self.assertFalse(game.shoot())  # weapon has a short firing cooldown
        for _ in range(3):
            game.step()
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

    def test_six_levels_have_reachable_exits_pickups_and_threats(self):
        game = games.Doom()
        self.assertEqual(game.level_count, 6)
        for index in range(game.level_count):
            game.load_level(index)
            self.assertEqual(len({len(row) for row in game.maze}), 1)
            reachable = game.distances((int(game.x), int(game.y)))
            self.assertEqual(len(reachable), sum(cell != "#" for row in game.maze for cell in row))
            self.assertIn(game.exit, reachable)
            self.assertTrue(all((int(enemy.x), int(enemy.y)) in reachable for enemy in game.enemies))
            self.assertTrue(all(tile in reachable for tile in game.pickups))
            self.assertEqual(game.total, 3 + index)
        self.assertEqual(game.enemies[-1].kind, "B")

    def test_gate_requires_clear_and_advances_preserving_score(self):
        game = games.Doom()
        game.x, game.y = game.exit[0] - 0.4, game.exit[1] + 0.5
        game.move(0.6, 0)
        self.assertEqual(game.level_index, 0)
        game.kills = game.total
        game.score = 300
        game.health = 40
        game.ammo = 8
        game.move(-0.6, 0)
        game.move(0.6, 0)
        self.assertEqual(game.level_index, 1)
        self.assertEqual((game.score, game.health, game.ammo), (300, 58, 20))
        game.load_level(5)
        game.kills = game.total
        game.x, game.y = game.exit[0] + 1.4, game.exit[1] + 0.5
        game.angle = math.pi
        game.move(0.6, 0)
        self.assertTrue(game.won)
        game.reset()
        self.assertEqual((game.level_index, game.score, game.health), (0, 0, 100))

    def test_medkit_ammo_and_projectile_damage(self):
        game = games.Doom()
        game.health, game.ammo = 55, 3
        game.pickups[(3, 1)] = "H"
        game.x, game.y = 2.6, 1.5
        game.move(0.5, 0)
        self.assertEqual(game.health, 85)
        game.pickups[(4, 1)] = "A"
        game.move(1.0, 0)
        self.assertEqual(game.ammo, 15)
        game.projectiles.append(games.Projectile(game.x + 0.5, game.y, -0.25, 0, 9))
        game.step()
        self.assertEqual(game.health, 76)
        game.projectiles.append(games.Projectile(game.x + 0.5, game.y, -0.25, 0, 9))
        game.step()
        self.assertEqual(game.health, 76)  # brief protection after a hit

    def test_emergency_ammo_prevents_softlock(self):
        game = games.Doom()
        game.ammo = 0
        game.pickups.clear()
        game.ticks = 99
        game.step()
        self.assertEqual(game.ammo, 6)

    def test_ranged_enemy_fires_and_boss_requires_sustained_fire(self):
        game = games.Doom()
        shooter = games.Enemy(5.5, 1.5, 2, "R")
        game.enemies = [shooter]
        game.total = 1
        game.step()
        self.assertEqual(len(game.projectiles), 1)
        self.assertEqual(game.projectiles[0].damage, 9)
        boss = games.Enemy(5.5, 1.5, 8, "B")
        game.enemies = [boss]
        game.projectiles.clear()
        game.ticks = 0
        for _ in range(8):
            self.assertTrue(game.shoot())
            for _ in range(3):
                game.step()
        self.assertEqual((boss.health, game.kills, game.score), (0, 1, 1000))


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

#!/usr/bin/env python3
"""
杀戮尖塔2 视觉识别系统
模块三：状态追踪器
"""

import os
import time
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import deque

@dataclass
class PlayerState:
    """玩家状态"""
    id: int
    name: str = ""
    hp: int = 0
    max_hp: int = 0
    block: int = 0
    energy: int = 0
    buffs: Dict[str, int] = field(default_factory=dict)
    
@dataclass
class DamageEvent:
    """伤害事件"""
    timestamp: float
    player_id: int
    target_type: str  # "enemy" or "player"
    damage: int
    source_card: str = ""
    
@dataclass
class FightEvent:
    """战斗事件"""
    timestamp: float
    event_type: str  # "fight_start", "fight_end", "card_play", "damage"
    data: Dict = field(default_factory=dict)


class StateTracker:
    """状态追踪器"""
    
    def __init__(self):
        # 玩家状态
        self.players: Dict[int, PlayerState] = {}
        
        # 历史记录
        self.damage_events: deque = deque(maxlen=1000)
        self.fight_events: deque = deque(maxlen=100)
        
        # 战斗状态
        self.in_fight = False
        self.fight_start_time = 0
        self.fight_number = 0
        
        # 上一帧状态（用于差分）
        self.previous_hp: Dict[int, int] = {}
    
    def update_player(self, player_id: int, hp: int = None, max_hp: int = None, 
                     block: int = None, energy: int = None, buffs: Dict = None):
        """更新玩家状态"""
        if player_id not in self.players:
            self.players[player_id] = PlayerState(id=player_id)
        
        player = self.players[player_id]
        
        # 检测伤害
        if hp is not None and player_id in self.previous_hp:
            old_hp = self.previous_hp[player_id]
            if hp < old_hp:
                damage = old_hp - hp
                self._record_damage(player_id, damage, "enemy_to_player")
        
        # 更新状态
        if hp is not None:
            player.hp = hp
        if max_hp is not None:
            player.max_hp = max_hp
        if block is not None:
            player.block = block
        if energy is not None:
            player.energy = energy
        if buffs:
            player.buffs.update(buffs)
        
        # 记录HP
        self.previous_hp[player_id] = hp if hp is not None else player.hp
    
    def update_enemy(self, enemy_id: int, hp: int = None, max_hp: int = None):
        """更新敌人状态"""
        if not hasattr(self, 'enemies'):
            self.enemies = {}
        
        if enemy_id not in self.enemies:
            self.enemies[enemy_id] = {"hp": 0, "max_hp": 0}
        
        enemy = self.enemies[enemy_id]
        
        # 检测伤害
        if hp is not None and enemy["hp"] > 0 and hp < enemy["hp"]:
            damage = enemy["hp"] - hp
            self._record_damage(0, damage, "player_to_enemy")  # 假设玩家0
        
        # 更新
        if hp is not None:
            enemy["hp"] = hp
        if max_hp is not None:
            enemy["max_hp"] = max_hp
    
    def _record_damage(self, player_id: int, damage: int, target_type: str):
        """记录伤害事件"""
        event = DamageEvent(
            timestamp=time.time(),
            player_id=player_id,
            target_type=target_type,
            damage=damage
        )
        self.damage_events.append(event)
    
    def start_fight(self):
        """开始战斗"""
        if not self.in_fight:
            self.in_fight = True
            self.fight_number += 1
            self.fight_start_time = time.time()
            
            event = FightEvent(
                timestamp=time.time(),
                event_type="fight_start",
                data={"fight_number": self.fight_number}
            )
            self.fight_events.append(event)
            print(f"\n=== 战斗 {self.fight_number} 开始 ===")
    
    def end_fight(self, victory: bool = False):
        """结束战斗"""
        if self.in_fight:
            self.in_fight = False
            
            event = FightEvent(
                timestamp=time.time(),
                event_type="fight_end",
                data={
                    "fight_number": self.fight_number,
                    "victory": victory,
                    "duration": time.time() - self.fight_start_time
                }
            )
            self.fight_events.append(event)
            print(f"=== 战斗 {self.fight_number} 结束 (胜利: {victory}) ===")
    
    def get_total_damage(self, player_id: int = None) -> int:
        """获取总伤害"""
        total = 0
        for event in self.damage_events:
            if event.target_type == "player_to_enemy":
                if player_id is None or event.player_id == player_id:
                    total += event.damage
        return total
    
    def get_dps(self, player_id: int = None) -> float:
        """计算DPS"""
        if not self.in_fight:
            return 0.0
        
        duration = time.time() - self.fight_start_time
        if duration <= 0:
            return 0.0
        
        damage = self.get_total_damage(player_id)
        return damage / duration
    
    def get_statistics(self) -> Dict:
        """获取统计数据"""
        stats = {
            "fight_number": self.fight_number,
            "in_fight": self.in_fight,
            "total_damage": self.get_total_damage(),
            "dps": self.get_dps(),
            "damage_events": len(self.damage_events),
            "players": {}
        }
        
        for pid, player in self.players.items():
            stats["players"][pid] = {
                "name": player.name,
                "hp": player.hp,
                "max_hp": player.max_hp,
                "block": player.block,
                "energy": player.energy,
                "damage_dealt": self.get_total_damage(pid)
            }
        
        return stats
    
    def export_report(self) -> str:
        """导出报告"""
        stats = self.get_statistics()
        
        report = f"""
================================================================================
                    杀戮尖塔2 战斗统计报告
================================================================================
战斗场次: {stats['fight_number']}
当前战斗: {'是' if stats['in_fight'] else '否'}

总伤害: {stats['total_damage']}
DPS: {stats['dps']:.1f}
伤害事件数: {stats['damage_events']}

玩家状态:
"""
        for pid, pdata in stats['players'].items():
            report += f"""
玩家 {pid}:
  HP: {pdata['hp']}/{pdata['max_hp']}
  护盾: {pdata['block']}
  能量: {pdata['energy']}
  造成伤害: {pdata['damage_dealt']}
"""
        return report
    
    def save_report(self, filename: str = None):
        """保存报告"""
        if filename is None:
            filename = f"fight_report_{int(time.time())}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.get_statistics(), f, indent=2, ensure_ascii=False)
        
        print(f"报告已保存: {filename}")


def test_tracker():
    """测试追踪器"""
    print("=" * 50)
    print("状态追踪器测试")
    print("=" * 50)
    
    tracker = StateTracker()
    
    # 模拟玩家
    tracker.update_player(0, hp=80, max_hp=80, energy=3)
    tracker.update_player(1, hp=75, max_hp=75, energy=3)
    
    # 开始战斗
    tracker.start_fight()
    
    # 模拟伤害
    tracker.update_enemy(0, hp=45)
    time.sleep(0.5)
    tracker.update_enemy(0, hp=30)
    time.sleep(0.5)
    tracker.update_enemy(0, hp=0)
    
    # 结束战斗
    tracker.end_fight(victory=True)
    
    # 统计
    print(tracker.export_report())
    tracker.save_report()


if __name__ == "__main__":
    test_tracker()

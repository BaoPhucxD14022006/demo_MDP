"""Huấn luyện mô hình Deep Reinforcement Learning (PPO) cho Robot AMR trong nhà kho.

Sử dụng:
- Stable-Baselines3 (PPO MlpPolicy)
- VecNormalize chuẩn hóa observation
- EvalCallback lưu lại model có phần thưởng tốt nhất
"""

from __future__ import annotations

import logging
from pathlib import Path
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, EvalCallback
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from warehouse_env import WarehouseAMREnv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class TrainingProgressCallback(BaseCallback):
    """Callback ghi log tiến trình huấn luyện sau mỗi 10,000 bước."""

    def __init__(self, check_freq: int = 10_000, verbose: int = 0) -> None:
        super().__init__(verbose)
        self.check_freq = check_freq

    def _on_step(self) -> bool:
        if self.n_calls % self.check_freq == 0:
            logger.info("[Tiến trình] Đã chạy %d bước huấn luyện...", self.num_timesteps)
        return True


def make_env() -> WarehouseAMREnv:
    """Tạo instance môi trường WarehouseAMREnv."""
    return WarehouseAMREnv()


def train(total_timesteps: int = 250_000, seed: int = 42) -> Path:
    """Huấn luyện PPO và lưu model cùng thống kê chuẩn hóa."""
    models_dir = Path("models")
    logs_dir = Path("logs")
    models_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger.info("[Bước 1/3] Khởi tạo 8 môi trường song song DummyVecEnv...")
    num_envs = 8
    vec_env = DummyVecEnv([make_env for _ in range(num_envs)])
    norm_env = VecNormalize(vec_env, norm_obs=True, norm_reward=False, clip_obs=10.0)

    # Môi trường đánh giá độc lập
    eval_vec_env = DummyVecEnv([make_env])
    eval_norm_env = VecNormalize(
        eval_vec_env, norm_obs=True, norm_reward=False, clip_obs=10.0, training=False
    )

    eval_callback = EvalCallback(
        eval_norm_env,
        best_model_save_path=str(models_dir),
        log_path=str(logs_dir),
        eval_freq=max(2000, 10_000 // num_envs),
        n_eval_episodes=10,
        deterministic=True,
        render=False,
    )
    progress_callback = TrainingProgressCallback(check_freq=5000)

    logger.info("[Bước 2/3] Thiết lập thuật toán PPO với MlpPolicy...")
    model = PPO(
        policy="MlpPolicy",
        env=norm_env,
        learning_rate=3e-4,
        n_steps=1024,
        batch_size=128,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.005,
        policy_kwargs=dict(net_arch=dict(pi=[128, 128], vf=[128, 128])),
        tensorboard_log=None,
        seed=seed,
        verbose=0,
    )

    logger.info("[Bước 3/3] Bắt đầu quá trình huấn luyện (%d timesteps)...", total_timesteps)
    model.learn(
        total_timesteps=total_timesteps,
        callback=[eval_callback, progress_callback],
    )

    # Đồng bộ thống kê chuẩn hóa từ môi trường huấn luyện sang môi trường đánh giá
    eval_norm_env.obs_rms = norm_env.obs_rms

    final_model_path = models_dir / "ppo_amr.zip"
    vecnorm_path = models_dir / "vecnorm.pkl"

    model.save(str(final_model_path))
    norm_env.save(str(vecnorm_path))

    logger.info("Đã lưu mô hình PPO tại: %s", final_model_path)
    logger.info("Đã lưu thống kê chuẩn hóa tại: %s", vecnorm_path)
    return final_model_path


if __name__ == "__main__":
    train(total_timesteps=200_000)

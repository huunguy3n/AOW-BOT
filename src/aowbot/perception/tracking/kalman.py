"""Kalman van toc khong doi (x, y, vx, vy), mo hinh gia toc nhieu trang. Thuan numpy, dt thuc tung buoc.

Khi khong co phep do (vat bi che): chi `predict` -> P tang, vi tri tiep tuc truot theo van toc (xu ly che khuat).
Tham so (accel_sigma, meas_sigma) do bang benchmark Phase 4, khong dat tuy y.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

F64 = NDArray[np.float64]


@dataclass(frozen=True)
class KalmanParams:
    accel_sigma: float = 200.0    # px/s^2: muc "bat ngo" cua gia toc (nhieu qua trinh)
    meas_sigma: float = 4.0       # px: nhieu phep do vi tri
    init_vel_sigma: float = 100.0 # px/s: bat dinh van toc ban dau


class KalmanCV:
    def __init__(self, x: float, y: float, p: KalmanParams) -> None:
        self.p = p
        self.x: F64 = np.array([x, y, 0.0, 0.0])
        self.P: F64 = np.diag([p.meas_sigma**2, p.meas_sigma**2, p.init_vel_sigma**2, p.init_vel_sigma**2])

    def predict(self, dt: float) -> None:
        if dt < 0:
            raise ValueError("dt < 0")
        F = np.eye(4)
        F[0, 2] = F[1, 3] = dt
        s2 = self.p.accel_sigma**2
        q = np.array([[dt**4 / 4, dt**3 / 2], [dt**3 / 2, dt**2]]) * s2
        Q = np.zeros((4, 4))
        Q[np.ix_([0, 2], [0, 2])] = q
        Q[np.ix_([1, 3], [1, 3])] = q
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q

    def update(self, z: tuple[float, float]) -> None:
        H = np.zeros((2, 4))
        H[0, 0] = H[1, 1] = 1.0
        R = np.eye(2) * self.p.meas_sigma**2
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ (np.array(z) - H @ self.x)
        self.P = (np.eye(4) - K @ H) @ self.P

    @property
    def position(self) -> tuple[float, float]:
        return float(self.x[0]), float(self.x[1])

    @property
    def velocity(self) -> tuple[float, float]:
        return float(self.x[2]), float(self.x[3])

    @property
    def position_sigma(self) -> float:
        """Do bat dinh vi tri (px) = can bac hai cua vet hiep phuong sai x, y."""
        return float(np.sqrt((self.P[0, 0] + self.P[1, 1]) / 2))

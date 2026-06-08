"""相机抽象层：支持 Basler 工业相机（pypylon）与普通 USB 摄像头（OpenCV）"""

from __future__ import annotations

from typing import Protocol

import cv2
import numpy as np

import config


class Camera(Protocol):
    def read(self) -> tuple[bool, np.ndarray | None]: ...

    def isOpened(self) -> bool: ...

    def release(self) -> None: ...


class OpenCVCamera:
    """基于 OpenCV VideoCapture 的 USB 摄像头封装。"""

    def __init__(self, index: int = config.CAMERA_INDEX) -> None:
        backend = getattr(cv2, f"CAP_{config.CAMERA_BACKEND}", cv2.CAP_ANY)
        self._cap = cv2.VideoCapture(index, backend)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(index)
        if self._cap.isOpened():
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

    def read(self) -> tuple[bool, np.ndarray | None]:
        ret, frame = self._cap.read()
        return ret, frame

    def isOpened(self) -> bool:
        return self._cap.isOpened()

    def release(self) -> None:
        self._cap.release()


class BaslerCamera:
    """基于 pypylon 的 Basler 工业相机封装，接口与 OpenCV VideoCapture 兼容。"""

    def __init__(self) -> None:
        from pypylon import pylon

        self._pylon = pylon
        self._camera: pylon.InstantCamera | None = None
        self._converter: pylon.ImageFormatConverter | None = None
        self._opened = False

        tl_factory = pylon.TlFactory.GetInstance()
        device = self._find_device(tl_factory)
        if device is None:
            return

        self._camera = pylon.InstantCamera(tl_factory.CreateDevice(device))
        self._camera.Open()
        self._configure()
        self._camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        self._converter = pylon.ImageFormatConverter()
        self._converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        self._converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        self._opened = True

    def _find_device(self, tl_factory) -> object | None:
        devices = tl_factory.EnumerateDevices()
        if not devices:
            return None

        serial = config.BASLER_SERIAL_NUMBER.strip()
        if not serial:
            return devices[0]

        for device in devices:
            if device.GetSerialNumber() == serial:
                return device
        return None

    def _configure(self) -> None:
        assert self._camera is not None
        camera = self._camera
        pylon = self._pylon

        if config.BASLER_WIDTH is not None:
            camera.Width.SetValue(config.BASLER_WIDTH)
        if config.BASLER_HEIGHT is not None:
            camera.Height.SetValue(config.BASLER_HEIGHT)

        pixel_format = config.BASLER_PIXEL_FORMAT
        if pixel_format and camera.PixelFormat.IsWritable():
            try:
                camera.PixelFormat.SetValue(pixel_format)
            except Exception:
                pass

        if config.BASLER_EXPOSURE_AUTO:
            if camera.ExposureAuto.IsWritable():
                camera.ExposureAuto.SetValue(config.BASLER_EXPOSURE_AUTO)
        elif config.BASLER_EXPOSURE_TIME_US is not None:
            if camera.ExposureAuto.IsWritable():
                camera.ExposureAuto.SetValue("Off")
            if camera.ExposureTime.IsWritable():
                camera.ExposureTime.SetValue(float(config.BASLER_EXPOSURE_TIME_US))

        if config.BASLER_GAIN is not None and camera.Gain.IsWritable():
            camera.Gain.SetValue(float(config.BASLER_GAIN))

        if config.BASLER_FRAME_RATE is not None and hasattr(camera, "AcquisitionFrameRateEnable"):
            if camera.AcquisitionFrameRateEnable.IsWritable():
                camera.AcquisitionFrameRateEnable.SetValue(True)
            if camera.AcquisitionFrameRate.IsWritable():
                camera.AcquisitionFrameRate.SetValue(float(config.BASLER_FRAME_RATE))

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self._opened or self._camera is None or self._converter is None:
            return False, None

        pylon = self._pylon
        grab_result = self._camera.RetrieveResult(
            config.BASLER_GRAB_TIMEOUT_MS,
            pylon.TimeoutHandling_Return,
        )
        if not grab_result.GrabSucceeded():
            grab_result.Release()
            return False, None

        try:
            image = self._converter.Convert(grab_result)
            frame = image.GetArray()
            if frame.ndim == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            return True, frame
        finally:
            grab_result.Release()

    def isOpened(self) -> bool:
        return self._opened

    def release(self) -> None:
        if self._camera is None:
            return
        if self._camera.IsGrabbing():
            self._camera.StopGrabbing()
        if self._camera.IsOpen():
            self._camera.Close()
        self._opened = False


def list_basler_devices() -> list[dict[str, str]]:
    """枚举已连接的 Basler 相机，返回型号与序列号列表。"""
    try:
        from pypylon import pylon
    except ImportError:
        return []

    devices = pylon.TlFactory.GetInstance().EnumerateDevices()
    return [
        {
            "model": device.GetModelName(),
            "serial": device.GetSerialNumber(),
            "friendly_name": device.GetFriendlyName(),
        }
        for device in devices
    ]


def open_camera(index: int = config.CAMERA_INDEX) -> Camera:
    """根据 config.CAMERA_TYPE 打开对应类型的相机。"""
    camera_type = config.CAMERA_TYPE.lower()
    if camera_type == "basler":
        return BaslerCamera()
    if camera_type == "opencv":
        return OpenCVCamera(index)
    raise ValueError(f"不支持的相机类型: {config.CAMERA_TYPE}，请使用 'basler' 或 'opencv'")

export const getDeviceInfo = () => {
    const userAgent = navigator.userAgent;
    let deviceType = "Unknown";

    if (/windows phone/i.test(userAgent)) {
      deviceType = "Windows Phone";
    } else if (/android/i.test(userAgent)) {
      deviceType = "Android";
    } else if (/iPad|iPhone|iPod/.test(userAgent) && !window.MSStream) {
      deviceType = "iOS";
    } else if (/Macintosh|MacIntel|MacPPC|Mac68K/i.test(userAgent)) {
      deviceType = "Mac";
    } else if (/Windows|Win32|Win64|Windows NT|WinCE/i.test(userAgent)) {
      deviceType = "Windows";
    } else if (/Linux/i.test(userAgent)) {
      deviceType = "Linux";
    }

    return deviceType;
};

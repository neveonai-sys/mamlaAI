/**
 * nativeFileUtils.js
 *
 * Helpers for native file operations on Android / iOS (Capacitor).
 * On web, falls back to the standard browser download anchor trick.
 *
 * Usage:
 *   import { saveAndShare } from '../../utils/nativeFileUtils';
 *   await saveAndShare(blob, 'court-order.pdf', 'application/pdf');
 */

import { Capacitor } from '@capacitor/core';
import { Filesystem, Directory } from '@capacitor/filesystem';
import { Share } from '@capacitor/share';

/**
 * Convert a Blob to a base64 string (without the data-URL prefix).
 */
function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      // result is "data:<mime>;base64,<data>" — strip the prefix
      const base64 = reader.result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * Save a blob to the device and open the system share sheet.
 * On web, triggers a browser download instead.
 *
 * @param {Blob}   blob      - The file data.
 * @param {string} filename  - e.g. "court-order.pdf" or "draft.docx"
 * @param {string} mimeType  - e.g. "application/pdf" or "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
 */
export async function saveAndShare(blob, filename, mimeType) {
  if (Capacitor.isNativePlatform()) {
    // Native path: write to cache dir, then share
    const base64 = await blobToBase64(blob);
    const result = await Filesystem.writeFile({
      path: filename,
      data: base64,
      directory: Directory.Cache,
    });
    await Share.share({
      title: filename,
      url: result.uri,
      dialogTitle: `Save or share ${filename}`,
    });
  } else {
    // Web path: standard anchor-click download
    const url = URL.createObjectURL(new Blob([blob], { type: mimeType }));
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }
}

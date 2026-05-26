// toast.js — non-component exports tách riêng để tránh lỗi Vite Fast Refresh
let _setToast = null;

export function registerToastSetter(fn) {
  _setToast = fn;
}

export function showToast(msg, type = "success") {
  _setToast?.(msg, type);
}
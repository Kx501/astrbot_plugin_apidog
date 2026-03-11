import { useEffect } from "react";

type Props = {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "确定",
  cancelLabel = "取消",
  onConfirm,
  onCancel,
}: Props) {
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="modal-backdrop"
      onClick={onCancel}
      onKeyDown={(e) => e.key === "Escape" && onCancel()}
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      aria-describedby="confirm-dialog-desc"
      tabIndex={0}
    >
      <div
        className="modal modal--confirm"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h3 id="confirm-dialog-title">{title}</h3>
        </div>
        <div className="modal-body">
          <p id="confirm-dialog-desc" className="confirm-dialog-message">
            {message}
          </p>
        </div>
        <div className="modal-footer button-row">
          <button type="button" className="app-header__btn" onClick={onConfirm}>
            {confirmLabel}
          </button>
          <button type="button" className="app-header__btn" onClick={onCancel}>
            {cancelLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

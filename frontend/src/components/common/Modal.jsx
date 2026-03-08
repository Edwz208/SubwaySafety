import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";

function Modal({ isOpen, onClose, title, children }) {
  return (
    <Dialog open={isOpen} as="div" className="relative z-50" onClose={onClose}>
      <div className="fixed inset-0 bg-black/40" aria-hidden="true" />

      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="w-full max-w-lg rounded-xl border border-border bg-card-surface p-6 shadow-md">
          {title ? (
            <DialogTitle className="mb-4 text-xl font-semibold text-text-primary">
              {title}
            </DialogTitle>
          ) : null}

          <div className="text-sm text-text-primary">
            {children}
          </div>
        </DialogPanel>
      </div>
    </Dialog>
  );
}

export default Modal;

(defun my-elisp-mode-hook ()
  (evil-leader/set-key "me" 'eval-last-sexp)
  (evil-leader/set-key "mb" 'eval-buffer))

(add-hook 'emacs-lisp-mode-hook 'company-mode)
(add-hook 'emacs-lisp-mode-hook 'my-elisp-mode-hook)

(require-package 'js2-mode)
(require 'js2-mode)

(defun my-javascript-mode-hook ()
  (modify-syntax-entry ?_ "w"))

(add-hook 'js2-mode-hook 'my-javascript-mode-hook)

(add-to-list 'auto-mode-alist '("\\.js\\'" . js2-mode))

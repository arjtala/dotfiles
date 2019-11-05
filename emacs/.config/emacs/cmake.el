(defun my-cmake-mode-hook ()
  (modify-syntax-entry ?_ "w") ;;Underscores count as words
  (setq helm-make-build-dir (string-join (list (projectile-project-root) "src/build/")))
  )

(add-hook 'cmake-mode-hook 'my-cmake-mode-hook)

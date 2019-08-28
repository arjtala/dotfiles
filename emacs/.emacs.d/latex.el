;; Latex 
(require-package 'auctex)


(defun my-LaTeX-mode-hook ()
  (reftex-mode)
  (auto-fill-mode)
  (outline-minor-mode)
 )


(add-hook 'LaTeX-mode-hook 'my-LaTeX-mode-hook)
(require-package 'gscholar-bibtex)


(with-eval-after-load 'gscholar-bibtex
  (defun gscholar-bibtex-save-and-close ()
    (interactive)
    (gscholar-bibtex-copy-bibtex-entry)
    )
  (define-key gscholar-bibtex-mode-map (kbd "j") 'gscholar-bibtex-next-item)
  (define-key gscholar-bibtex-mode-map (kbd "k") 'gscholar-bibtex-previous-item)
  (define-key gscholar-bibtex-mode-map (kbd "RET") 'gscholar-bibtex-append-bibtex-to-database)
  )

Mamla.ai product screenshots
============================

Drop the real app screenshots here using these EXACT filenames. They are
served at /screenshots/<name>.png and copied into dist/ at build time
(see the CopyWebpackPlugin pattern in webpack.common.js).

Expected files:

  dashboard.png   - Practice dashboard / case repository overview
  drafting.png    - AI legal drafting editor (with AI Assistant panel)
  calendar.png    - Legal calendar (month view)
  ecourt.png      - eCourts / district court case search
  cases.png       - New Case modal / case management
  doc-intel.png   - Document Intelligence & Q&A (talk to docs)

Notes:
- Use PNG. A 16:10-ish aspect ratio looks best in the framed previews.
- Missing files degrade gracefully (a labelled placeholder shows instead),
  so the site never breaks if a screenshot has not been added yet.
- Where they appear:
    * Landing (/)        -> dashboard.png, drafting.png, ecourt.png
                            (ProductPreviewSection)
    * Features (/features)-> drafting / ecourt / calendar / doc-intel / cases
                            (FeaturesSection cards)

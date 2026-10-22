# Claim photo damage analysis

The AI Assessment page can analyze image files attached to a claim as `Photos` documents.
The backend runs both YOLOv8 segmentation checkpoints and saves detections under
`claim.ai_assessment.visual_damage_analysis`.

## Files and setup

- `models/damage_model.pt`: damage labels such as dent, scratch, crack, flat tire, and severe deformation.
- `models/parts_model.pt`: vehicle part segmentation labels.
- Install backend dependencies with `python -m pip install -r backend/requirements.txt`.

The authenticated staff endpoint is `POST /api/v1/ai/analyze-damage/` with JSON
`{"claim_id": 123}`. It analyzes supported JPG, PNG, WEBP, and BMP documents already
attached to the claim with document type `photos`. Results include each damage label,
the most overlapping detected part when available, confidence, and bounding box.

In the app, open **AI Assessment**, select the claim, and choose **Analyze Claim Photos**.
The endpoint reports a clear error if the claim has no supported photos or the model
runtime is not installed. These detections are visual evidence only; the models do not
estimate repair prices or make claim decisions.

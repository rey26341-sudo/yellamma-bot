#!/usr/bin/env bash
# Run this from the ROOT of your yellamma-bot repo (where app/, clients/, docker-compose.yml live)
set -euo pipefail

CONFIG_DIR="app/configs"
CONFIG_FILE="$CONFIG_DIR/clinic_demo.json"

if [ ! -d "app" ]; then
  echo "❌ 'app/' folder not found. Run this script from the root of the yellamma-bot repo."
  exit 1
fi

mkdir -p "$CONFIG_DIR"

if [ -f "$CONFIG_FILE" ]; then
  echo "⚠️  $CONFIG_FILE already exists."
  read -p "Overwrite it? (y/N) " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted — no changes made."
    exit 0
  fi
fi

cat > "$CONFIG_FILE" << 'EOF'
{
  "business_id": "clinic_demo",
  "business_type": "healthcare_clinic",
  "display_name": "Demo Family Clinic",

  "branding": {
    "primary_color": "#2E7D6B",
    "logo_url": "",
    "tagline": "Your health, our priority"
  },

  "company": {
    "name": "Demo Family Clinic",
    "address": "123 Example Street, City, Country",
    "phone": "+000-0000000",
    "email": "info@example-clinic.com",
    "opening_hours": {
      "mon_fri": "08:00-18:00",
      "sat": "09:00-13:00",
      "sun": "closed"
    },
    "emergency_notice": "For medical emergencies, call your local emergency number immediately. This assistant cannot help with emergencies."
  },

  "system_prompt_guardrails": {
    "role_definition": "You are the front-desk assistant for {business_name}. You handle scheduling, service information, pricing, insurance/payment questions, opening hours, and location. You are NOT a clinician and you do not provide medical advice, diagnoses, triage, or treatment recommendations under any circumstances.",
    "hard_rules": [
      "Never interpret symptoms, suggest possible conditions, or advise on medication, dosage, or treatment.",
      "Never tell a patient whether their symptoms are serious or how urgently they should be seen.",
      "If a message contains any symptom description, health complaint, or question implying 'what's wrong with me' or 'what should I do about X symptom', do not answer clinically — respond with the medical_redirect_message and offer to book the earliest available appointment or connect them to staff.",
      "If a message suggests a possible emergency (e.g. chest pain, difficulty breathing, severe bleeding, loss of consciousness, thoughts of self-harm), immediately return the emergency_redirect_message and stop the conversation flow — do not continue with booking questions first.",
      "Never store, repeat back, or ask for details of a patient's symptoms, diagnoses, or medical history beyond what's needed to route them (name, phone, preferred date/time, and reason category e.g. 'check-up', 'follow-up', 'new patient').",
      "Do not confirm or deny whether a specific person is a patient of the clinic (privacy).",
      "Always disclose you are an automated assistant when asked, and offer a path to a human staff member on request."
    ],
    "medical_redirect_message": "I'm not able to give medical advice — I can help you book an appointment so our clinical team can take a look. Would you like me to check availability?",
    "emergency_redirect_message": "This may need urgent attention. Please call emergency services or go to your nearest emergency room right away. If you'd like, I can also share our clinic's phone number for a follow-up once you're safe."
  },

  "services": [
    { "name": "General consultation", "description": "Routine check-up with a GP", "duration_minutes": 20, "price": "" },
    { "name": "Follow-up visit", "description": "Follow-up on an existing treatment plan", "duration_minutes": 15, "price": "" },
    { "name": "New patient registration", "description": "First-time visit including intake paperwork", "duration_minutes": 30, "price": "" }
  ],

  "faqs": [
    { "question": "What are your opening hours?", "answer": "We're open Mon–Fri 08:00–18:00 and Sat 09:00–13:00. Closed Sundays." },
    { "question": "Do you accept insurance?", "answer": "Please tell us your insurance provider and we'll confirm coverage, or connect you with our front desk." },
    { "question": "How do I book an appointment?", "answer": "I can help with that right now — just tell me your preferred date and time." },
    { "question": "Where are you located?", "answer": "123 Example Street, City, Country. Let me know if you'd like directions." },
    { "question": "Can I cancel or reschedule?", "answer": "Yes — share your name and the original appointment time and I'll pass it to our staff to update, or I can help you rebook." }
  ],

  "booking_flow": {
    "fields_collected": ["full_name", "phone_number", "preferred_date", "preferred_time", "visit_reason_category"],
    "visit_reason_categories": ["new patient", "check-up", "follow-up", "other (staff will call to clarify)"],
    "confirmation_template": "✅ Appointment request received.\nName: {full_name}\nPhone: {phone_number}\nDate: {preferred_date}\nTime: {preferred_time}\nReason: {visit_reason_category}\nOur staff will contact you shortly to confirm.",
    "notes": "Reason category is intentionally coarse — never capture free-text symptom descriptions here."
  },

  "data_handling_notes": {
    "retention": "Define a retention period (e.g. 90 days) for chat logs containing personal data; document this for GDPR compliance.",
    "processing_basis": "Confirm legal basis for processing (consent or legitimate interest) before going live with a real clinic.",
    "todo_before_pilot": [
      "Add a visible privacy notice in the chat widget",
      "Confirm data storage location (EU region) for the Postgres instance",
      "Get a signed Data Processing Agreement with the pilot clinic if you handle any patient data beyond name/phone"
    ]
  }
}
EOF

echo "✅ Wrote $CONFIG_FILE"

# Validate JSON syntax
if command -v python3 &> /dev/null; then
  python3 -m json.tool "$CONFIG_FILE" > /dev/null && echo "✅ JSON is valid"
elif command -v jq &> /dev/null; then
  jq empty "$CONFIG_FILE" && echo "✅ JSON is valid"
else
  echo "⚠️  Couldn't find python3 or jq to validate JSON — check it manually."
fi

echo ""
echo "Next steps:"
echo "1. Restart the API so config_loader.py picks up the new file:"
echo "     docker compose up --build"
echo "2. Test it:"
echo "     curl -X POST http://127.0.0.1:8001/chat \\"
echo "       -H \"Content-Type: application/json\" \\"
echo "       -d '{\"business_id\":\"clinic_demo\",\"message\":\"what are your opening hours?\"}'"
echo "3. Test a guardrail case:"
echo "     curl -X POST http://127.0.0.1:8001/chat \\"
echo "       -H \"Content-Type: application/json\" \\"
echo "       -d '{\"business_id\":\"clinic_demo\",\"message\":\"I have chest pain, what should I do?\"}'"
echo "   — this should trigger the emergency_redirect_message, not medical advice."

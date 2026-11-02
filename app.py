import streamlit as st
import json
import re
from html import escape
from google import genai
from google.genai import types

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="NutriScanAI",
    page_icon="🥗",
    layout="wide"
)

# --------------------------------------------------
# GEMINI CONFIGURATION
# --------------------------------------------------

MODEL_NAME = "gemini-3.8-flash"

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except Exception:
    st.error(
        "Gemini API key not found. Add GEMINI_API_KEY "
        "to .streamlit/secrets.toml."
    )
    st.stop()


# --------------------------------------------------
# HEALTH AND ALLERGY RULES
# --------------------------------------------------

HEALTH_RULES = {
    "High Blood Pressure": {
        "keywords": ["high blood pressure", "high bp"],
        "sodium": 460
    },
    "Diabetes": {
        "keywords": ["diabetes"],
        "added_sugar": 10
    },
    "Kidney Disease": {
        "keywords": ["kidney disease"],
        "sodium": 460
    },
    "Heart Disease": {
        "keywords": ["heart disease"],
        "sodium": 460,
        "saturated_fat": 4
    },
    "High Cholesterol": {
        "keywords": ["high cholesterol"],
        "saturated_fat": 4
    },
    "Obesity": {
        "keywords": ["obesity"],
        "calories": 400
    },
    "Fatty Liver": {
        "keywords": ["fatty liver"],
        "added_sugar": 10
    },
    "Gastric Problems": {
        "keywords": ["gastric problems"],
        "ingredients": [
            "chilli", "chili", "hot pepper",
            "black pepper", "caffeine"
        ]
    },
    "Kidney Stones": {
        "keywords": ["kidney stones"],
        "ingredients": [
            "spinach", "beetroot", "rhubarb",
            "almond", "peanut"
        ]
    }
}

ALLERGY_RULES = {
    "Peanut Allergy": ["peanut"],
    "Milk Allergy": [
        "milk", "whey", "casein", "milk powder",
        "cream", "butter", "cheese"
    ],
    "Wheat Allergy": ["wheat"],
    "Gluten Allergy / Celiac Disease": [
        "wheat", "barley", "rye", "malt", "gluten"
    ],
    "Egg Allergy": ["egg", "albumin"],
    "Soy Allergy": ["soy", "soya"],
    "Fish Allergy": ["fish"],
    "Shellfish Allergy": [
        "shrimp", "prawn", "crab", "lobster", "shellfish"
    ],
    "Sesame Allergy": ["sesame"],
    "Almond Allergy": ["almond"],
    "Cashew Allergy": ["cashew"],
    "Walnut Allergy": ["walnut"]
}

INTOLERANCE_RULES = {
    "Lactose Intolerance": [
        "lactose", "milk powder", "whey", "casein"
    ],
    "Gluten Intolerance": [
        "wheat", "barley", "rye", "malt", "gluten"
    ],
    "Fructose Intolerance": [
        "fructose", "high fructose corn syrup"
    ]
}


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def normalize_text(value):
    return str(value).lower().strip()


def clean_list(value):
    if not isinstance(value, list):
        return []
    return [
        str(item).strip()
        for item in value
        if str(item).strip()
    ]


def get_nutrient_value(nutrition, key):
    value = nutrition.get(key, "UNKNOWN")

    if isinstance(value, (int, float)):
        return float(value)

    match = re.search(r"\d+(\.\d+)?", str(value))

    if match:
        return float(match.group())

    return None


def ingredient_found(ingredient_text, keywords):
    text = normalize_text(ingredient_text)

    return any(
        re.search(
            r"(?<![a-z])" + re.escape(word.lower()) + r"(?![a-z])",
            text
        )
        for word in keywords
    )


def display_bullets(items):
    if not items:
        st.write("• No information available")
        return

    for item in items:
        st.markdown(f"• {escape(str(item))}")


def display_fields(data):
    for key, value in data.items():
        st.markdown(
            f"• **{escape(str(key).replace('_', ' ').title())}:** "
            f"{escape(str(value))}"
        )


def analyze_health_conditions(nutrition, ingredients):
    concerns = []

    sodium = get_nutrient_value(nutrition, "sodium_mg")
    added_sugar = get_nutrient_value(nutrition, "added_sugars_g")
    saturated_fat = get_nutrient_value(
        nutrition, "saturated_fat_g"
    )
    calories = get_nutrient_value(nutrition, "calories")

    ingredient_text = " ".join(ingredients).lower()

    if sodium is not None and sodium >= 460:
        concerns.extend([
            "High Blood Pressure",
            "Kidney Disease",
            "Heart Disease"
        ])

    if added_sugar is not None and added_sugar >= 10:
        concerns.extend(["Diabetes", "Fatty Liver"])

    if saturated_fat is not None and saturated_fat >= 4:
        concerns.extend(["Heart Disease", "High Cholesterol"])

    if calories is not None and calories >= 400:
        concerns.append("Obesity")

    for condition in ["Gastric Problems", "Kidney Stones"]:
        keywords = HEALTH_RULES[condition]["ingredients"]

        if ingredient_found(ingredient_text, keywords):
            concerns.append(condition)

    return list(dict.fromkeys(concerns))


def analyze_allergies(ingredients):
    ingredient_text = " ".join(ingredients).lower()
    warnings = []

    for allergy, keywords in ALLERGY_RULES.items():
        if ingredient_found(ingredient_text, keywords):
            warnings.append(allergy)

    return warnings


def get_personal_warnings(
    conditions,
    allergies,
    intolerances,
    other_conditions,
    health_concerns,
    allergy_warnings,
    ingredients
):
    warnings = []

    health_text = " ".join(health_concerns).lower()
    allergy_text = " ".join(allergy_warnings).lower()
    ingredient_text = " ".join(ingredients).lower()

    condition_map = {
        "Diabetes": ["diabetes"],
        "High Blood Pressure": ["high blood pressure"],
        "Kidney Disease": ["kidney disease"],
        "Heart Disease": ["heart disease"],
        "High Cholesterol": ["high cholesterol"],
        "Obesity": ["obesity"],
        "Fatty Liver": ["fatty liver"],
        "Gastric Problems": ["gastric problems"],
        "Kidney Stones": ["kidney stones"]
    }

    for condition in conditions:
        keywords = condition_map.get(condition, [])

        if any(word in health_text for word in keywords):
            warnings.append(
                f"{condition}: A possible food-related concern "
                "was identified from the available nutrition "
                "and ingredient information."
            )

    for allergy in allergies:
        if allergy.lower() in allergy_text:
            warnings.append(
                f"{allergy}: A possible allergen match was detected. "
                "Check the complete food label carefully."
            )

    for intolerance in intolerances:
        keywords = INTOLERANCE_RULES.get(intolerance, [])

        if ingredient_found(ingredient_text, keywords):
            warnings.append(
                f"{intolerance}: A potentially relevant ingredient "
                "was detected. Check the food label."
            )

    if other_conditions.strip():
        warnings.append(
            f"Other condition entered: {other_conditions}. "
            "Automatic assessment is not available for this entry."
        )

    return warnings


def get_risk_score(data):
    try:
        score = int(data.get("risk_score", 0))
        return max(0, min(100, score))
    except (ValueError, TypeError):
        return 0


# --------------------------------------------------
# CSS DESIGN
# --------------------------------------------------

st.markdown("""
<style>

.stApp {
    background-color: #F4FAF5;
}

.hero {
    background: linear-gradient(120deg, #123F2B, #24764A);
    padding: 35px 20px;
    border-radius: 18px;
    text-align: center;
    color: white;
    margin-bottom: 25px;
}

.hero h1 {
    color: white;
    font-size: 42px;
    font-weight: 800;
}

.hero p {
    color: #E1F4E7;
    font-size: 17px;
}

.section-card {
    background: white;
    border: 1px solid #CDE6D2;
    padding: 20px;
    border-radius: 14px;
    margin-bottom: 18px;
}

.risk-card {
    background: white;
    border: 1px solid #CDE6D2;
    padding: 22px;
    border-radius: 15px;
    text-align: center;
}

.risk-number {
    font-size: 40px;
    font-weight: 800;
    color: #123F2B;
}

.risk-label {
    font-size: 22px;
    font-weight: bold;
}

div.stButton > button {
    background-color: #B7E4C7;
    color: #123F2B;
    border: none;
    border-radius: 10px;
    font-weight: bold;
    padding: 10px 35px;
}

div.stButton > button:hover {
    background-color: #95D5AA;
    color: #123F2B;
}

</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# HERO SECTION
# --------------------------------------------------

st.markdown("""
<div class="hero">
    <p>AI-POWERED NUTRITION ASSISTANT</p>
    <h1>🥗 NutriScanAI</h1>
    <p>Know Your Food. Make Smarter Choices.</p>
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# PERSONAL HEALTH PROFILE
# --------------------------------------------------

st.markdown("## 🩺 Personal Health Profile")

st.caption(
    "Select your conditions to receive personalized food warnings. "
    "All fields are optional."
)

with st.container(border=True):

    selected_conditions = st.multiselect(
        "Medical Conditions",
        [
            "Diabetes",
            "High Blood Pressure",
            "Kidney Disease",
            "Heart Disease",
            "High Cholesterol",
            "Obesity",
            "Fatty Liver",
            "Gastric Problems",
            "Kidney Stones"
        ],
        key="medical_conditions"
    )

    selected_allergies = st.multiselect(
        "Food Allergies",
        list(ALLERGY_RULES.keys()),
        key="food_allergies"
    )

    selected_intolerances = st.multiselect(
        "Food Intolerances",
        list(INTOLERANCE_RULES.keys()),
        key="food_intolerances"
    )

    other_conditions = st.text_input(
        "Other Conditions (Optional)",
        placeholder="Enter another condition or intolerance"
    )


# --------------------------------------------------
# IMAGE UPLOAD
# --------------------------------------------------

st.markdown("## 📸 Upload Your Food Image")

uploaded_file = st.file_uploader(
    "Upload a food image or food packet image",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    st.image(
        uploaded_file,
        caption="Uploaded Food Image",
        use_container_width=True
    )


# --------------------------------------------------
# ANALYZE BUTTON
# --------------------------------------------------

if st.button("🔍 Analyze Food", use_container_width=True):

    if uploaded_file is None:
        st.warning("Please upload a food image first.")

    else:

        with st.spinner("Analyzing your food..."):

            prompt = """
You are NutriScanAI, an AI-powered food and nutrition assistant.

Analyze the uploaded food image carefully.

Return ONLY valid JSON with this exact structure:

{
  "food_name": "",
  "flavour": "",
  "category": "",
  "food_type": "",
  "serving_size": "",
  "nutrition": {
    "calories": "",
    "protein_g": "",
    "carbohydrates_g": "",
    "fats_g": "",
    "added_sugars_g": "",
    "saturated_fat_g": "",
    "sodium_mg": ""
  },
  "ingredients": [],
  "added_colours": [],
  "preservatives": [],
  "other_additives": [],
  "chemical_combination_risk": "",
  "risk_score": 0,
  "risk_reason": "",
  "age_recommendations": {
    "Below 5 years": "",
    "5-12 years": "",
    "13-18 years": "",
    "19-59 years": "",
    "60+ years": ""
  }
}

IMPORTANT INSTRUCTIONS:

1. Identify the food name, flavour, category and food type.

2. For packaged food, read the visible ingredient and nutrition labels.
   Use whole-packet values only if the packet size and label values
   allow a reliable calculation. Otherwise state the serving size.

3. For natural foods such as apples, bananas and vegetables,
   estimate nutrition for the visible edible portion.

4. Do not treat naturally occurring sugar as added sugar.

5. If a value cannot be identified reliably, return "UNKNOWN".
   Never invent ingredient names or nutrition values.

6. Identify added colours, preservatives and other additives.
   If none are identified, return an empty list.

7. Mention a chemical combination risk only when there is an
   established concern. Otherwise return:
   "No specific combination risk identified."

8. Give a food risk score from 0 to 100:
   0-40 = LOW RISK
   41-69 = MODERATE RISK
   70-100 = HIGH RISK

   This is a general AI estimate, not a medical diagnosis.

9. For each age group, return ONLY one of:
   "Avoid", "Consume in limit", "Should not consume".

10. Keep the risk reason short.

11. Return all values in the JSON structure.
"""

            try:

                image_bytes = uploaded_file.getvalue()

                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=uploaded_file.type
                        ),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )

                result = json.loads(response.text)

                food_name = result.get("food_name", "UNKNOWN")
                nutrition = result.get("nutrition", {})
                ingredients = clean_list(result.get("ingredients", []))
                added_colours = clean_list(
                    result.get("added_colours", [])
                )
                preservatives = clean_list(
                    result.get("preservatives", [])
                )
                other_additives = clean_list(
                    result.get("other_additives", [])
                )

                # ------------------------------------------
                # FOOD IDENTIFICATION
                # ------------------------------------------

                st.success("Food analysis completed successfully!")

                st.markdown("## 🍎 Food Identification")

                display_fields({
                    "Food Name": food_name,
                    "Flavour": result.get("flavour", "UNKNOWN"),
                    "Category": result.get("category", "UNKNOWN"),
                    "Food Type": result.get("food_type", "UNKNOWN"),
                    "Serving Size": result.get("serving_size", "UNKNOWN")
                })

                # ------------------------------------------
                # NUTRITION
                # ------------------------------------------

                st.markdown("## 🥗 Nutritional Information")

                display_fields({
                    "Calories": nutrition.get("calories", "UNKNOWN"),
                    "Protein": nutrition.get("protein_g", "UNKNOWN"),
                    "Carbohydrates": nutrition.get(
                        "carbohydrates_g", "UNKNOWN"
                    ),
                    "Fats": nutrition.get("fats_g", "UNKNOWN"),
                    "Added Sugars": nutrition.get(
                        "added_sugars_g", "UNKNOWN"
                    ),
                    "Saturated Fat": nutrition.get(
                        "saturated_fat_g", "UNKNOWN"
                    ),
                    "Sodium": nutrition.get("sodium_mg", "UNKNOWN")
                })

                st.caption(
                    "General adult daily reference: "
                    "2000 kcal, 50 g protein, 275 g carbohydrates "
                    "and 78 g fats. Actual needs vary by individual."
                )

                # ------------------------------------------
                # INGREDIENTS AND ADDITIVES
                # ------------------------------------------

                st.markdown("## 🧾 Ingredients")
                display_bullets(ingredients)

                st.markdown("## 🎨 Added Colours")
                display_bullets(added_colours)

                st.markdown("## 🧪 Preservatives")
                display_bullets(preservatives)

                st.markdown("## ⚗️ Other Additives")
                display_bullets(other_additives)

                st.markdown("## ⚠️ Chemical Combination Risk")
                st.write(
                    result.get(
                        "chemical_combination_risk",
                        "UNKNOWN"
                    )
                )

                # ------------------------------------------
                # RISK SCORE
                # ------------------------------------------

                risk_score = get_risk_score(result)

                if risk_score <= 40:
                    risk_label = "LOW RISK"
                    risk_color = "#28A745"

                elif risk_score <= 69:
                    risk_label = "MODERATE RISK"
                    risk_color = "#FFC107"

                else:
                    risk_label = "HIGH RISK"
                    risk_color = "#DC3545"

                st.markdown("## 📊 Overall Food Risk Score")

                st.markdown(
                    f"""
                    <div class="risk-card">
                        <div class="risk-number">
                            {risk_score}/100
                        </div>
                        <div class="risk-label"
                             style="color: {risk_color};">
                            {risk_label}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown("**Reason:**")
                st.write(result.get("risk_reason", "UNKNOWN"))

                # ------------------------------------------
                # AGE RECOMMENDATIONS
                # ------------------------------------------

                st.markdown("## 👨‍👩‍👧 Age Recommendations")

                age_recommendations = result.get(
                    "age_recommendations", {}
                )

                display_fields(age_recommendations)

                # ------------------------------------------
                # AUTOMATIC HEALTH CONCERNS
                # ------------------------------------------

                health_concerns = analyze_health_conditions(
                    nutrition,
                    ingredients
                )

                st.markdown("## 🩺 General Health Concerns")

                if health_concerns:
                    display_bullets(health_concerns)
                else:
                    st.write(
                        "No matching concerns identified by "
                        "the preliminary screening rules."
                    )

                # ------------------------------------------
                # AUTOMATIC ALLERGY CHECK
                # ------------------------------------------

                allergy_warnings = analyze_allergies(ingredients)

                st.markdown("## 🚨 Detected Allergen Ingredients")

                if allergy_warnings:
                    display_bullets(allergy_warnings)
                else:
                    st.write(
                        "No listed allergen ingredients were "
                        "identified in the detected ingredient list."
                    )

                # ------------------------------------------
                # PERSONALIZED HEALTH REPORT
                # ------------------------------------------

                personal_warnings = get_personal_warnings(
                    selected_conditions,
                    selected_allergies,
                    selected_intolerances,
                    other_conditions,
                    health_concerns,
                    allergy_warnings,
                    ingredients
                )

                st.markdown("## 🩺 Personalized Health Report")

                if personal_warnings:

                    for warning in personal_warnings:
                        st.warning(warning)

                else:
                    st.success(
                        "No matching concerns were identified "
                        "from your selected profile and the "
                        "available food information."
                    )

                st.caption(
                    "Important: NutriScanAI provides preliminary "
                    "information, not medical advice. Ingredient "
                    "detection may be incomplete. People with serious "
                    "allergies or medical conditions should verify "
                    "the complete label and consult a qualified "
                    "health professional."
                )

            except json.JSONDecodeError:
                st.error(
                    "The AI returned an invalid response. "
                    "Please try again."
                )

            except Exception as e:
                st.error(
                    f"Food analysis failed: {str(e)}"
                )

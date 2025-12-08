from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

class TextInput(BaseModel):
    text: str

app = FastAPI()

@app.on_event("startup")
def load_model():
    global nlp
    model_dir = "/app/hf_cache"
    model_name = "obi/deid_roberta_i2b2"

    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=model_dir)
    model = AutoModelForTokenClassification.from_pretrained(model_name, cache_dir=model_dir)

    nlp = pipeline(
        "token-classification",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple"
    )

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/redact")
def redact(input_data: TextInput):
    entities = nlp(input_data.text)
    entities.sort(key=lambda x: x['start'], reverse=True)
    redacted = input_data.text
    for e in entities:
        redacted = redacted[:e['start']] + f"[{e['entity_group']}]" + redacted[e['end']:]
    return {"redacted": redacted}

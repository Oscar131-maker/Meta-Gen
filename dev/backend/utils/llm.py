import json
from openai import OpenAI
from anthropic import Anthropic

def analyze_content(scraped_data, openai_api_key, system_prompt, user_prompt_template):
    client = OpenAI(api_key=openai_api_key)
    
    content_block = ""
    if isinstance(scraped_data, dict):
        content_block = f"""
RESULTADO FINAL:
============================================================
🔗 URL: {scraped_data.get('url', 'N/A')}
📌 H1:  {scraped_data.get('h1', 'N/A')}
------------------------------------------------------------
📄 TEXTO COMPLETO:
{scraped_data.get('full_text', '')}
"""
    else:
        content_block = f"""
{scraped_data}
"""

    human_message = f"{user_prompt_template}\n\n## Texto de la web:\n{content_block}\n----------------"
    
    print(f"DEBUG: Enviando prompt Directo a OpenAI.")
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.03,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": human_message}
        ]
    )
    
    content = response.choices[0].message.content
    print(f"DEBUG: Respuesta raw de OpenAI: {content!r}") 
    
    cleaned_content = content
    if content.strip().startswith("```"):
        cleaned_content = content.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(cleaned_content), system_prompt, human_message
    except json.JSONDecodeError as e:
        error_report = f"""
        FALLO CRÍTICO EN PARSEO JSON DE OPENAI
        ---------------------------------------
        Error: {str(e)}
        Raw Content:
        {content}
        ---------------------------------------
        Cleaned Content:
        {cleaned_content}
        """
        raise Exception(error_report)

def generate_meta_tags(analysis_json, text_content, serp_results, openrouter_api_key, system_prompt, user_prompt_template):
    # Using OpenRouter via OpenAI SDK
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=openrouter_api_key,
    )
    
    human_message = f"""
{user_prompt_template}

## Información de la página web
{json.dumps(analysis_json, ensure_ascii=False, indent=2)}

## Texto de la página web
{text_content}

## Resultados de la SERP
{json.dumps(serp_results, ensure_ascii=False, indent=2)}
"""

    print(f"DEBUG: Enviando consulta a OpenRouter (Claude 3.7 Sonnet)...")

    response = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "http://localhost:8000", # Local development
            "X-Title": "MetaGen Local",
        },
        model="anthropic/claude-3.7-sonnet",
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": human_message}
        ]
    )
    
    return response.choices[0].message.content, system_prompt, human_message

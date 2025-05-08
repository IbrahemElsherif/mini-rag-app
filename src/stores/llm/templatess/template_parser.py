import os
import re

class TemplateParser:
    
    def __init__(self, language: str=None, default_language='en'):
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.default_language = default_language
        self.language = None

        self.set_language(language)

    def set_language(self, language: str):
        if not language:
            self.language = self.default_language

        language_path = os.path.join(self.current_path, "locales", language)
        if os.path.exists(language_path):
            self.language = language
        else:
            self.language = self.default_language

    def get(self, group: str, key: str, variables: dict={}):
        if not group or not key:
            return None

        group_path = os.path.join(self.current_path, "locales", self.language, f"{group}.py" )
        targeted_language = self.language
        if not os.path.exists(group_path):
            group_path = os.path.join(self.current_path, "locales", self.default_language, f"{group}.py" )
            targeted_language = self.default_language

        if not os.path.exists(group_path):
            return None

        # import group module
        module = __import__(f"stores.llm.templatess.locales.{targeted_language}.{group}", fromlist=[group])

        if not module:
            return None

        key_attribute = getattr(module, key)
        return key_attribute.substitute(variables)

    def force_arabic_response(self, response: str):
        """Force response to be in Arabic if English is detected"""
        # Check if response contains primarily English
        english_chars = re.findall(r'[a-zA-Z]', response)
        if len(english_chars) > len(response) * 0.3:  # If more than 30% is English
            return "عذراً، لا توجد لدي معلومات كافية عن هذا الموضوع. يرجى التواصل مع المعهد السعودي العالي للحصول على مزيد من المعلومات."
        return response
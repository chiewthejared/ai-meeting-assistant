import google.generativeai as genai
import os
from typing import Dict
import json
import re

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.available = False
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Try newer model names
                model_names = ['gemini-2.5-flash', 'gemini-2.5-pro']
                for model_name in model_names:
                    try:
                        self.model = genai.GenerativeModel(model_name)
                        # Test with a simple prompt
                        test_response = self.model.generate_content("Say 'OK'")
                        if test_response and test_response.text:
                            self.available = True
                            print(f"✅ Gemini initialized with model: {model_name}")
                            break
                    except Exception as e:
                        print(f"⚠️ Model {model_name} failed: {e}")
                        continue
                
                if not self.available:
                    print("⚠️ No Gemini model available. Using mock mode.")
            except Exception as e:
                print(f"⚠️ Gemini initialization failed: {e}")
                print("⚠️ Using mock mode for LLM")
        else:
            print("⚠️ GEMINI_API_KEY not found")
            print("⚠️ Using mock mode for LLM")
    
    def _extract_json_from_text(self, text: str) -> Dict:
        """Extract JSON from Gemini's response text"""
        print(f"📝 Attempting to parse Gemini response...")
        
        # Clean the text first
        text = text.strip()
        
        # Try multiple approaches to extract JSON
        approaches = [
            # Approach 1: Find JSON between ```json and ```
            lambda: re.search(r'```json\s*([\s\S]*?)\s*```', text),
            # Approach 2: Find JSON between ``` and ```
            lambda: re.search(r'```\s*([\s\S]*?)\s*```', text),
            # Approach 3: Find anything that looks like a JSON object (most flexible)
            lambda: re.search(r'\{[\s\S]*\}', text),
            # Approach 4: Handle responses that start with "json" or "JSON"
            lambda: re.search(r'^(?:json|JSON)\s*(\{[\s\S]*\})', text, re.IGNORECASE),
        ]
        
        for approach in approaches:
            match = approach()
            if match:
                try:
                    json_str = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    # Clean up the string
                    json_str = json_str.strip()
                    
                    # Remove markdown code block markers if present
                    json_str = re.sub(r'^```(?:json)?\s*', '', json_str)
                    json_str = re.sub(r'\s*```$', '', json_str)
                    
                    # Fix common JSON issues
                    # Remove trailing commas before closing braces/brackets
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    
                    try:
                        result = json.loads(json_str)
                        print("✅ Successfully parsed JSON")
                        return result
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON parse error: {e}")
                        
                        # Try to fix common issues
                        # Look for the first { and last }
                        start = json_str.find('{')
                        end = json_str.rfind('}') + 1
                        if start != -1 and end > start:
                            try:
                                fixed_str = json_str[start:end]
                                # Remove any trailing commas
                                fixed_str = re.sub(r',\s*}', '}', fixed_str)
                                fixed_str = re.sub(r',\s*]', ']', fixed_str)
                                result = json.loads(fixed_str)
                                print("✅ Successfully parsed JSON after cleanup")
                                return result
                            except:
                                pass
                        
                        # If still failing, try to extract with regex
                        print("🔄 Attempting manual extraction with regex...")
                        return self._manual_extract(json_str)
                        
                except Exception as e:
                    print(f"⚠️ Approach failed: {e}")
                    continue
        
        # If all approaches fail, try manual extraction
        print("🔄 Attempting manual extraction...")
        return self._manual_extract(text)
    
    def _manual_extract(self, text: str) -> Dict:
        """Manually extract summary, action items, and decisions from text"""
        print("🔄 Manual extraction from text...")
        
        # Clean the text
        text = text.strip()
        
        # Try to find sections using common patterns
        summary = ""
        action_items = []
        decisions = []
        
        # Look for summary section - multiple patterns
        summary_patterns = [
            r'(?:summary|meeting summary|summary of the meeting)[\s:]*([^.]*\.)',
            r'["\']summary["\']\s*:\s*["\']([^"\']*)["\']',
            r'["\']summary["\']\s*:\s*(?:["\'])?([^"\']*)(?:["\'])?',
        ]
        
        for pattern in summary_patterns:
            summary_match = re.search(pattern, text, re.IGNORECASE)
            if summary_match:
                summary_text = summary_match.group(1).strip()
                # Clean up any leftover JSON artifacts
                summary_text = re.sub(r'^["\']+', '', summary_text)
                summary_text = re.sub(r'["\']+$', '', summary_text)
                summary_text = re.sub(r'^\{+', '', summary_text)
                summary_text = re.sub(r'\}+$', '', summary_text)
                if summary_text:
                    summary = summary_text
                    break
        
        # If no summary found, try to get first few sentences
        if not summary:
            sentences = re.findall(r'[^.!?]*[.!?]', text)
            if sentences:
                # Find first sentence that contains meaningful content
                for sent in sentences[:5]:
                    if len(sent.strip()) > 20 and ('meeting' in sent.lower() or 'discuss' in sent.lower() or 'team' in sent.lower()):
                        summary = sent.strip()
                        break
                if not summary:
                    summary = ' '.join(sentences[:2]).strip() if sentences else "Summary could not be extracted."
        
        # Look for action items
        action_patterns = [
            r'(?:action items|actionables|tasks|to do|next steps)[\s:]*([\s\S]*?)(?=\n\s*(?:decisions|conclusions|$))',
            r'["\']action_items["\']\s*:\s*\[([^\]]*)\]',
            r'["\']action_items["\']\s*:\s*(?:["\'])?([^"\']*)(?:["\'])?',
        ]
        
        for pattern in action_patterns:
            action_match = re.search(pattern, text, re.IGNORECASE)
            if action_match:
                action_text = action_match.group(1)
                # Look for bullet points or numbered items
                bullets = re.findall(r'[•\-*]\s*([^\n]+)', action_text)
                if bullets:
                    action_items = [b.strip() for b in bullets]
                else:
                    # Split by numbers or commas
                    items = re.findall(r'\d+\.\s*([^\n]+)', action_text)
                    if items:
                        action_items = [i.strip() for i in items]
                    else:
                        # Split by comma if no bullets/numbers
                        items = [i.strip() for i in action_text.split(',') if i.strip()]
                        if items and len(items) > 1:
                            action_items = items
                        else:
                            # Just take the whole text
                            action_items = [action_text.strip()]
                if action_items:
                    break
        
        # If no action items found, try to find them in the full text
        if not action_items:
            # Look for sentences with action-related keywords
            sentences = re.split(r'[.!?]\s+', text)
            for sent in sentences:
                sent_lower = sent.lower()
                if any(kw in sent_lower for kw in ['will', 'need to', 'should', 'must', 'task', 'action']):
                    clean = sent.strip()
                    if len(clean) > 10:
                        action_items.append(clean)
                if len(action_items) >= 3:
                    break
        
        # If still no action items, provide a default
        if not action_items:
            action_items = ["No action items clearly identified in the meeting."]
        
        # Look for decisions
        decision_patterns = [
            r'(?:decisions|conclusions|agreed|outcome)[\s:]*([\s\S]*?)(?=\n\s*(?:summary|action|$))',
            r'["\']decisions["\']\s*:\s*\[([^\]]*)\]',
            r'["\']decisions["\']\s*:\s*(?:["\'])?([^"\']*)(?:["\'])?',
        ]
        
        for pattern in decision_patterns:
            decision_match = re.search(pattern, text, re.IGNORECASE)
            if decision_match:
                decision_text = decision_match.group(1)
                bullets = re.findall(r'[•\-*]\s*([^\n]+)', decision_text)
                if bullets:
                    decisions = [b.strip() for b in bullets]
                else:
                    items = re.findall(r'\d+\.\s*([^\n]+)', decision_text)
                    if items:
                        decisions = [i.strip() for i in items]
                    else:
                        items = [i.strip() for i in decision_text.split(',') if i.strip()]
                        if items and len(items) > 1:
                            decisions = items
                        else:
                            decisions = [decision_text.strip()]
                if decisions:
                    break
        
        # If no decisions found, try to find them in the full text
        if not decisions:
            sentences = re.split(r'[.!?]\s+', text)
            for sent in sentences:
                sent_lower = sent.lower()
                if any(kw in sent_lower for kw in ['decid', 'agreed', 'conclud', 'resolve', 'approved']):
                    clean = sent.strip()
                    if len(clean) > 10:
                        decisions.append(clean)
                if len(decisions) >= 3:
                    break
        
        if not decisions:
            decisions = ["No decisions clearly identified in the meeting."]
        
        # Clean up the summary
        summary = re.sub(r'^["\']+', '', summary)
        summary = re.sub(r'["\']+$', '', summary)
        summary = re.sub(r'^\{+', '', summary)
        summary = re.sub(r'\}+$', '', summary)
        
        # Truncate summary if too long
        if len(summary) > 800:
            summary = summary[:800] + "..."
        
        # Clean action items and decisions
        action_items = [re.sub(r'^["\']+', '', a) for a in action_items]
        action_items = [re.sub(r'["\']+$', '', a) for a in action_items]
        decisions = [re.sub(r'^["\']+', '', d) for d in decisions]
        decisions = [re.sub(r'["\']+$', '', d) for d in decisions]
        
        # Limit number of items
        action_items = action_items[:10]
        decisions = decisions[:10]
        
        print("✅ Manual extraction complete")
        return {
            "summary": summary if summary else "Summary could not be extracted from the transcript.",
            "action_items": action_items,
            "decisions": decisions
        }
    
    def generate_summary(self, transcript: str) -> Dict:
        """Generate summary from transcript using Gemini"""
        
        if self.available:
            try:
                # Truncate transcript if too long (Gemini has token limits)
                if len(transcript) > 8000:
                    transcript = transcript[:8000] + "..."
                
                prompt = f"""
                Analyze this meeting transcript and provide:
                1. Summary (2-3 concise paragraphs summarizing the main discussion)
                2. Action Items (list of specific tasks mentioned, with owners if any)
                3. Decisions Made (list of decisions agreed upon)
                
                Transcript: {transcript}
                
                Return ONLY valid JSON with exactly these keys:
                {{
                    "summary": "your summary text here",
                    "action_items": ["action 1", "action 2"],
                    "decisions": ["decision 1", "decision 2"]
                }}
                
                Important: Make sure the JSON is valid with proper commas and quotes.
                Do not include any text outside the JSON object.
                """
                
                print("🔄 Calling Gemini API...")
                response = self.model.generate_content(prompt)
                response_text = response.text
                print(f"📝 Gemini response length: {len(response_text)}")
                
                # Try to extract JSON
                result = self._extract_json_from_text(response_text)
                
                # Validate and clean the result
                if "summary" not in result or not result["summary"] or result["summary"].startswith("{"):
                    result["summary"] = "No summary generated from the transcript."
                if "action_items" not in result or not result["action_items"]:
                    result["action_items"] = ["No specific action items found in the meeting."]
                if "decisions" not in result or not result["decisions"]:
                    result["decisions"] = ["No specific decisions found in the meeting."]
                
                # Clean the summary - remove any leftover JSON artifacts
                summary = result["summary"]
                if isinstance(summary, str):
                    summary = re.sub(r'^[\s"\'{]+', '', summary)
                    summary = re.sub(r'[\s"\'}]+$', '', summary)
                    result["summary"] = summary
                
                print("✅ Summary generated successfully")
                return result
                
            except Exception as e:
                print(f"⚠️ Gemini API error: {e}")
                print("🔄 Falling back to mock mode")
        
        # MOCK RESPONSE (only if Gemini fails)
        print("🔄 Using mock summary generation...")
        return {
            "summary": "The transcript was processed, but Gemini was unable to generate a summary. Please check your API key and try again.",
            "action_items": ["Check Gemini API key", "Try again after resolving any errors"],
            "decisions": ["Not available - summary generation failed"]
        }
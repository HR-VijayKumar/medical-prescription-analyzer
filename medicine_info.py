import os
import json
import time
import random
import re
from typing import Dict, List
from playwright.sync_api import sync_playwright
import google.generativeai as genai
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import backoff
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key from .env file
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found. Please check your .env file.")

# Initialize the Gemini model
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')

def human_delay(min_seconds, max_seconds):
    """Add a random delay to simulate human behavior"""
    time.sleep(random.uniform(min_seconds, max_seconds))

def select_medication_website(page):
    """Select a specific website from search results"""
    # Priority list of trusted medical websites
    preferred_domains = [
        "1mg.com",
        "apollopharmacy.in",
        "webmd.com",
        "mayoclinic.org",
        "drugs.com",
        "rxlist.com",
        "nih.gov",
        "medlineplus.gov",
        "pharmeasy.in",
        "netmeds.com"
    ]
    
    # Wait for search results to load
    try:
        page.wait_for_selector('h3')
        human_delay(1, 2)
        
        # Get all available links
        all_links = page.locator('h3').all()
        print(f"Found {len(all_links)} search result links")
        
        # Try to select from preferred domains first
        for domain in preferred_domains:
            for i, link in enumerate(all_links):
                try:
                    parent = link.locator('xpath=..').first
                    url_text = parent.get_attribute('href') or ""
                    
                    if domain in url_text:
                        print(f"Selected result #{i+1} with domain {domain}")
                        all_links[i].click()
                        page.wait_for_load_state('networkidle')
                        return page.url
                except Exception as e:
                    continue
        
        # If no preferred domain was found, select the first result
        try:
            print("No preferred domain found, selecting first result")
            all_links[0].click()
            page.wait_for_load_state('networkidle')
            return page.url
        except Exception as e:
            print(f"Failed to click first result: {e}")
            return None
    except Exception as e:
        print(f"Error in selecting website: {e}")
        return None

def search_single_medicine(page, misspelled_medicine):
    """Search for a single medicine and return the corrected name and URL"""
    # Go to Google
    page.goto("https://www.google.com")
    human_delay(1, 2)
    
    # Accept cookies if prompted
    if page.locator('button:has-text("Accept all")').is_visible():
        page.locator('button:has-text("Accept all")').click()
        human_delay(1, 2)
    
    # Use the search input
    search_selectors = ['textarea.gLFyf', '#APjFqb', 'textarea[name="q"]']
    
    for selector in search_selectors:
        if page.locator(selector).is_visible():
            # Type like a human
            element = page.locator(selector)
            element.click()
            human_delay(0.5, 1)
            
            element.fill("")
            human_delay(0.5, 1)
            
            for char in misspelled_medicine:
                element.type(char, delay=random.randint(50, 150))
            
            human_delay(0.5, 1)
            page.press(selector, "Enter")
            break
    
    # Wait for results
    page.wait_for_load_state('networkidle')
    
    # Check for spelling corrections
    corrected_spelling = misspelled_medicine
    
    # Look for "Did you mean" suggestion
    did_you_mean = page.locator('a:has-text("Did you mean")').first
    if did_you_mean.is_visible():
        try:
            suggestion = page.locator('a.gL9Hy, i').inner_text()
            print(f"Google suggested: {suggestion}")
            corrected_spelling = suggestion
            human_delay(1, 2)
            page.locator('a.gL9Hy, .spell_orig a').first.click()
            human_delay(1, 3)
        except:
            print("Found 'Did you mean' but couldn't extract the text")
    
    # Look for "Showing results for" auto-correction
    showing_results = page.locator('p:has-text("Showing results for"), .spell_orig').first
    if showing_results.count() > 0:
        try:
            correction = page.locator('.spell_orig a, .spell b').inner_text()
            corrected_spelling = correction
            print(f"Google automatically corrected to: {correction}")
        except:
            print("Google made an automatic correction but couldn't extract the text")
    
    print(f"Using medicine name: {corrected_spelling}")
    
    # Select a medication website
    url = select_medication_website(page)
    
    if url:
        print(f"Selected URL: {url}")
        return corrected_spelling, url
    else:
        print(f"Failed to select a website for {corrected_spelling}")
        return corrected_spelling, None

def extract_medicine_name_from_url(page, url):
    """Extract the actual medicine name from the pharmacy website"""
    try:
        # Different extraction methods based on the website domain
        if "apollopharmacy.in" in url:
            # For Apollo Pharmacy
            # First try to get the product title
            product_title = page.locator('.ProductDetailsGeneric-name, .ProductCard-title, h1.MuiTypography-root').first
            if product_title.is_visible():
                name = product_title.inner_text().strip()
                return name
                
            # Fallback: extract from URL
            match = re.search(r'/medicine/([^?]+)', url)
            if match:
                medicine_slug = match.group(1)
                # Convert slug to readable name
                medicine_name = medicine_slug.replace('-', ' ')
                medicine_name = re.sub(r'\d+mg|\d+\s*s$', '', medicine_name)  # Remove dosage and packaging info
                medicine_name = medicine_name.replace('tablet', '').strip()
                return medicine_name.title()  # Title case the name
        
        elif "1mg.com" in url:
            # For 1mg.com
            product_title = page.locator('.DrugHeader__title-content, .style__pro-title, h1').first
            if product_title.is_visible():
                return product_title.inner_text().strip()
        
        elif "netmeds.com" in url:
            # For Netmeds
            product_title = page.locator('.product-detail, .product_title, h1').first
            if product_title.is_visible():
                return product_title.inner_text().strip()
        
        elif "pharmeasy.in" in url:
            # For PharmEasy
            product_title = page.locator('.MedicineOverviewSection_medicineName, .ProductTitle_medicineName, h1').first
            if product_title.is_visible():
                return product_title.inner_text().strip()
                
        # Generic fallback for other websites
        title = page.locator('h1').first
        if title.is_visible():
            return title.inner_text().strip()
            
        # If all else fails, extract from URL
        url_parts = url.split('/')
        for part in url_parts:
            if len(part) > 3 and '-' in part and '?' not in part:
                return part.replace('-', ' ').title()
                
        return None
    except Exception as e:
        print(f"Error extracting medicine name: {e}")
        return None

def convert_html_to_markdown(html_content, url):
    """
    Convert HTML to clean markdown, removing unnecessary elements
    and preserving important content.
    """
    try:
        # First use BeautifulSoup to clean up the HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements that typically contain irrelevant content
        for element in soup.select('script, style, nav, footer, iframe, .cookie-banner, .popup, .modal, .advertisement, .ad, .banner, aside, [role=banner], [role=complementary]'):
            element.decompose()
        
        # Try to identify the main content area
        main_content = None
        potential_content_selectors = [
            'main', 
            'article', 
            '#content', 
            '.content', 
            '.main', 
            '.main-content', 
            '.product-detail',
            '.drug-info',
            '.medicine-info',
            '.product-description',
            'div[role=main]'
        ]
        
        for selector in potential_content_selectors:
            elements = soup.select(selector)
            if elements:
                # Use the first matching content area that has substantial text
                for element in elements:
                    if len(element.get_text(strip=True)) > 200:
                        main_content = element
                        break
                if main_content:
                    break
        
        # If we couldn't find a suitable main content area, use the body
        if not main_content:
            main_content = soup.body
        
        # Convert cleaned HTML to markdown
        markdown_content = md(str(main_content), heading_style="ATX")
        
        # Clean up the markdown
        # Remove excess newlines
        markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
        
        # Add the source URL at the end
        markdown_content += f"\n\nSource URL: {url}"
        
        return markdown_content
    
    except Exception as e:
        print(f"Error converting HTML to markdown: {e}")
        return f"Failed to convert content: {str(e)}"

@backoff.on_exception(
    backoff.expo,
    (Exception),
    max_tries=3,
    jitter=backoff.full_jitter
)
def extract_medicine_info(markdown_content: str, medicine_name: str) -> Dict:
    """Extract structured information from markdown using Gemini API with retry capability"""
    prompt = f"""
    You are a pharmaceutical data extraction specialist. I have markdown content about the medicine "{medicine_name}" from a pharmaceutical website.
    
    Here is the markdown content to analyze:
    ```
    {markdown_content[:20000]}  # Using markdown allows more content within token limits
    ```
    
    Extract and provide the following information in JSON format:
    
    1. Correct Medicine Name: The official or standard name of the medicine (if different from "{medicine_name}")
    2. Description: A concise description of what this medicine is and what it treats
    3. Key Benefits: Main benefits and uses of the medicine (list format)
    4. Directions for Use: How to use this medicine properly
    5. Safety Information: Important safety warnings, side effects, and contraindications
    6. Relevant Information: Any other critical information about the medicine (dosage, storage, etc.)
    
    Respond ONLY with a JSON object that has these keys: "medicine_name", "description", "key_benefits", "directions", "safety_info", and "relevant_info".
    For any section where information is not available, use an empty string or empty list as appropriate.
    """

    try:
        response = gemini_model.generate_content(
            prompt, 
            generation_config={
                "temperature": 0.1,  # Lower temperature for more factual extraction
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 4000,
                "response_mime_type": "application/json"
            }
        )
        
        # Extract the JSON from the response
        response_text = response.text
        
        # Handle case where response might have markdown code blocks
        if "```json" in response_text:
            json_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_text = response_text.split("```")[1].strip()
        else:
            json_text = response_text.strip()
        
        # Clean the JSON string - handle potential formatting issues
        json_text = json_text.replace('\n', ' ').replace('\\', '\\\\')
        
        # Parse the JSON
        try:
            result = json.loads(json_text)
        except json.JSONDecodeError:
            # Try more aggressive cleanup if standard parsing fails
            json_text = re.sub(r'[^\x00-\x7F]+', '', json_text)  # Remove non-ASCII chars
            result = json.loads(json_text)
        
        # If medicine_name is not in the result, add the provided one
        if "medicine_name" not in result or not result["medicine_name"]:
            result["medicine_name"] = medicine_name
            
        # Ensure all required keys exist
        required_keys = ["medicine_name", "description", "key_benefits", "directions", "safety_info", "relevant_info"]
        for key in required_keys:
            if key not in result:
                if key == "key_benefits":
                    result[key] = []
                else:
                    result[key] = ""
                    
        return result
    
    except Exception as e:
        print(f"Error extracting information for {medicine_name}: {e}")
        # Return a default structure in case of error
        return {
            "medicine_name": medicine_name,
            "description": f"Error extracting information: {str(e)}",
            "key_benefits": [],
            "directions": "",
            "safety_info": "",
            "relevant_info": ""
        }

def process_medicine_list(medicine_list, headless=True):
    """Process a list of medicines and save the results to a JSON file"""
    results = []
    success_count = 0
    
    # Start Playwright once for all medicines
    with sync_playwright() as playwright:
        # Launch a single browser instance
        browser = playwright.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Create a single context for all operations
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        
        # Create a single page that will be reused for all searches
        page = context.new_page()
        page.set_default_timeout(60000)  # 60 second timeout
        
        for i, medicine_name in enumerate(medicine_list):
            print(f"\n>>> Processing medicine {i+1}/{len(medicine_list)}: {medicine_name}")
            
            try:
                # Phase 1: Search for medicine and get URL
                search_term = f"{medicine_name} medicine links"
                corrected_name, url = search_single_medicine(page, search_term)
                
                if not url:
                    print(f"✗ Failed to find a URL for {medicine_name}")
                    results.append({
                        "medicine_name": medicine_name,
                        "description": "Failed to find a reliable URL for this medicine",
                        "key_benefits": [],
                        "directions": "",
                        "safety_info": "",
                        "relevant_info": "",
                        "url": ""
                    })
                    continue
                
                # Extract actual medicine name from the URL page if possible
                actual_medicine_name = extract_medicine_name_from_url(page, url)
                if actual_medicine_name:
                    corrected_name = actual_medicine_name
                    print(f"Identified medicine name: {corrected_name}")
                
                # Phase 2: Extract content from the page
                html_content = page.content()
                markdown_content = convert_html_to_markdown(html_content, url)
                
                # Phase 3: Process with Gemini API
                info = extract_medicine_info(markdown_content, corrected_name)
                info["url"] = url
                
                # Verify we got meaningful data
                if info["description"] and not info["description"].startswith("Error"):
                    success_count += 1
                    print(f"✓ Successfully processed {corrected_name}")
                else:
                    print(f"✗ Failed to extract proper information for {corrected_name}")
                
                results.append(info)
                
                # Add delay between medicines to avoid rate limiting
                if i < len(medicine_list) - 1:
                    human_delay(2, 4)
                    
            except Exception as e:
                print(f"Error processing {medicine_name}: {e}")
                results.append({
                    "medicine_name": medicine_name,
                    "description": f"Error: {str(e)}",
                    "key_benefits": [],
                    "directions": "",
                    "safety_info": "",
                    "relevant_info": "",
                    "url": ""
                })
        
        # Close the browser when all medicines have been processed
        page.close()
        browser.close()
    
    # Format the results for output
    medicine_data = {}
    for info in results:
        medicine_name = info["medicine_name"]
        
        # Format key benefits as a string
        benefits = info["key_benefits"]
        if isinstance(benefits, list):
            benefits_str = ", ".join(benefits)
        else:
            benefits_str = str(benefits)
        
        # Create entry for this medicine
        medicine_data[medicine_name] = {
            "description": info["description"],
            "key_benefits": benefits_str,
            "directions": info["directions"],
            "safety_info": info["safety_info"],
            "relevant_info": info["relevant_info"],
            "url": info.get("url", ""),
        }
    
    # Print success rate
    print(f"\nProcessed {len(medicine_list)} medicines with {success_count} successes ({success_count/len(medicine_list)*100:.1f}% success rate)")
    
    return medicine_data

if __name__ == "__main__":
    # Example usage
    medicine_list = ['ullracet']
    
    # Process the medicines
    medicine_data = process_medicine_list(
        medicine_list,
        headless=True  # Always use headless mode
    )
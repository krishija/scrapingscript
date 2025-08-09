#!/usr/bin/env python3
"""
Quick test script to verify contact extraction is working.
Just tests the qualitative engine on a single university.
"""

import os
from dotenv import load_dotenv
from qualitative_engine import QualitativeEngine

def test_contacts():
    # Load environment
    load_dotenv()
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    
    if not gemini_api_key:
        print("❌ GEMINI_API_KEY not found in .env file")
        return
    
    # Test universities
    test_universities = [
        "Texas Christian University",
        "The University of Alabama", 
        "Tulane University of Louisiana"
    ]
    
    engine = QualitativeEngine(gemini_api_key)
    
    for university in test_universities:
        print(f"\n{'='*60}")
        print(f"🎯 TESTING CONTACT EXTRACTION: {university}")
        print('='*60)
        
        try:
            result = engine.run(university)
            
            # Check for contacts
            contacts = result.get("student_contacts", result.get("social_leaders", []))
            emails_found = result.get("contacts_with_email", result.get("leaders_with_email", 0))
            
            print(f"\n📊 RESULTS:")
            print(f"   Contacts Found: {len(contacts)}")
            print(f"   With Emails: {emails_found}")
            
            if contacts:
                print(f"\n📧 CONTACTS:")
                for i, contact in enumerate(contacts, 1):
                    name = contact.get("name", "Unknown")
                    email = contact.get("email", "No email")
                    title = contact.get("title", "Unknown title")
                    org = contact.get("organization", "Unknown org")
                    
                    print(f"   {i}. {name}")
                    print(f"      Title: {title}")
                    print(f"      Org: {org}")
                    print(f"      Email: {email}")
                    
                    if "@" in email:
                        print(f"      ✅ Valid email format")
                    else:
                        print(f"      ❌ No valid email")
                    print()
            else:
                print(f"   ❌ No contacts extracted")
                
        except Exception as e:
            print(f"❌ Failed to process {university}: {e}")

if __name__ == "__main__":
    test_contacts()

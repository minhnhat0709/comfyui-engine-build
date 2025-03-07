
from supabase import Client, create_client
import os

url: str = os.environ.get('SUPABASE_ENDPOINT') or "https://rtfoijxfymuizzxzbnld.supabase.co"
key: str = os.environ.get('SUPABASE_KEY') or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ0Zm9panhmeW11aXp6eHpibmxkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTY5NjU3NzgxNCwiZXhwIjoyMDEyMTUzODE0fQ.huosB8bfQgkZ_YY7-E67YB5HbFsPjAM7rTg2Jt54x7M"
supabase: Client = create_client(url, key)



parent_tags =  ['interior', 'architecture']
tags = ['townhouse', 'villa', 'house', 'apartment', 'office', 'hotel', 'restaurant', 'bar', 'cafe', 'shop', 'school', 'hospital', 'park', 'library', 'museum', 'art', 'music', 'sport', 'travel', 'technology', 'other']

loras = supabase.table("Models").select("*").eq("type", "lora").execute().data

for tag in parent_tags:
    supabase.table("tags").insert({"name": tag, "parent_id": None}).execute()
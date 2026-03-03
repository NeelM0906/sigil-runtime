# Data Acquisition Method - LOCKED

*Locked: 2026-02-27*
*Verified working approach for Google Sheets public data*

---

## The Working Method: Direct CSV Export via curl

When GOG authentication fails or Google Sheets are public, use direct export:

```bash
curl -L "https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}" -o output.csv
```

### Parameters:
- `SHEET_ID`: The long alphanumeric ID from the sheet URL
- `GID`: The specific tab ID (found in URL as `gid=XXXXX`)
- `-L`: Follow redirects (required for Google's redirect chain)

---

## Example (Lawyer Contact List)

```bash
# Sheet: Seamless Lawyer List 2/27/26
# Tab: "List for SAI" (gid=447682998)

curl -L "https://docs.google.com/spreadsheets/d/1sgSFbI3IXK4Tx_wzCVAq3PgZrAIoCQ_h_hrNmnnz1FE/export?format=csv&gid=447682998" -o /tmp/seamless_lawyers.csv
```

**Result:** 126,356 contacts, 48.9MB CSV

---

## Why This Works

1. Google Sheets supports direct export URLs for public sheets
2. No authentication required for "Anyone with the link" sheets
3. Bypasses GOG CLI keyring issues entirely
4. Fast download (46.6MB in ~7 seconds)

---

## When to Use This

- GOG authentication is broken (`aes.KeyUnwrap(): integrity check failed`)
- Sheet is public ("Anyone with the link can view")
- Need bulk data extraction without browser automation
- Chrome relay isn't available

---

## Alternative: Browser Automation

If curl doesn't work (private sheets), use OpenClaw browser:

1. Open sheet with `browser action=open`
2. Navigate to File → Download → CSV
3. Wait for download to complete
4. Check `~/Downloads/` for the file

---

## Column Structure (Lawyer List)

```
First Name, Last Name, Bio, Title, Department, Seniority,
Company Name - Cleaned, Website, List, Contact LI Profile URL,
Email 1, Email 1 Validation, Email 1 Total AI,
Email 2, Email 2 Validation, Email 2 Total AI,
Personal Email, Personal Email Validation, Personal Email Total AI,
Contact Phone 1, Company Phone 1, Contact Phone 2, Company Phone 2,
Contact Phone 3, Company Phone 3, Contact Mobile Phone,
Contact Mobile Phone 1 Total AI, Contact Mobile Phone 2,
Contact Mobile Phone 2 Total AI, Contact Mobile Phone 3,
Contact City, Contact Mobile Phone 3 Total AI, Contact State,
Contact State Abbr, Contact Country, Contact Country (Alpha 2),
Contact Country (Alpha 3), Contact Country - Numeric,
Contact Location, Company Location, Company City, Company State,
Company State Abbr, Company Post Code, Company Country,
Company Country (Alpha 2), Company Country (Alpha 3),
Company Country - Numeric, Company Annual Revenue,
Company Description, Company Website Domain, Company Founded Date,
Company Industry, Company LI Profile Url, Company Revenue Range,
Company Staff Count, Company Staff Count Range, SIC Code, NAICS Code
```

---

## File Location

Saved to: `data/seamless_lawyers.csv`

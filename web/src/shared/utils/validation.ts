// Client-side checks for instant feedback only. The API validates everything again.

/** Tanzanian mobile numbers: 0712 345 678, 712345678, 255712345678, +255 712 345 678. */
export const TZ_PHONE = /^(?:\+?255|0)?\s*[67]\d{2}[\s-]?\d{3}[\s-]?\d{3}$/;

export const PASSWORD_RULE = /^(?=.*[A-Za-z])(?=.*\d).{8,128}$/;

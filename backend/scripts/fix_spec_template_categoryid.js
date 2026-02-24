/**
 * MongoDB Script to Fix specTemplates.categoryId Type
 * =====================================================
 * 
 * This script converts categoryId from string to ObjectId in the specTemplates collection.
 * Run this in MongoDB Compass or mongosh against your b2b_marketplace database.
 *
 * Instructions:
 * 1. Open MongoDB Compass and connect to your Cluster0
 * 2. Select the b2b_marketplace database
 * 3. Open the embedded mongosh shell (click ">_MONGOSH" at bottom)
 * 4. Copy and paste this entire script
 * 5. Press Enter to run
 */

// Switch to the correct database
use("b2b_marketplace");

// Find all specTemplates where categoryId is a string
const templates = db.specTemplates.find({
  categoryId: { $type: "string" }
}).toArray();

print(`Found ${templates.length} specTemplates with string categoryId`);

// Fix each template
let fixedCount = 0;
templates.forEach(template => {
  try {
    const newCategoryId = ObjectId(template.categoryId);
    
    db.specTemplates.updateOne(
      { _id: template._id },
      { $set: { categoryId: newCategoryId } }
    );
    
    print(`Fixed: ${template.name} - categoryId converted to ObjectId`);
    fixedCount++;
  } catch (e) {
    print(`Error fixing ${template.name}: ${e.message}`);
  }
});

print(`\nDone! Fixed ${fixedCount}/${templates.length} templates`);

// Verify the fix
const remaining = db.specTemplates.countDocuments({
  categoryId: { $type: "string" }
});
print(`Remaining templates with string categoryId: ${remaining}`);

// Show all templates with their category info
print("\n=== Current specTemplates Status ===");
db.specTemplates.find({}).forEach(t => {
  const cat = db.categories.findOne({ _id: t.categoryId });
  print(`${t.name}: categoryId=${t.categoryId} (type: ${typeof t.categoryId}) -> category: ${cat ? cat.name : "NOT FOUND"}`);
});

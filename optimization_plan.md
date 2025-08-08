# Tavily Optimization Plan

## Current Usage: ~65 calls per university
## Target: ~35 calls per university (-46% reduction)

### Phase 1: Query Consolidation (Immediate -40%)
1. **Quantitative Engine**: 18 → 12 calls
   - Reduce each metric from 3 to 2 strategic queries
   - Prioritize Common Data Set + site:.edu queries

2. **Contact Finder**: 24 → 16 calls  
   - Reduce homepage discovery from 4 to 2 queries
   - Combine entity-specific searches

### Phase 2: Smart Early Exit (-25%)
1. Add confidence-based termination
2. Skip additional queries when high-confidence data found
3. Implement in quantitative_engine.py first

### Phase 3: Cross-Engine Sharing (-15%)
1. Create shared campus context object
2. Reuse discovered entity names
3. Cache domain patterns

### Phase 4: PDF Output
1. Install reportlab: `pip install reportlab`
2. Create pdf_generator.py with structured template
3. Include charts for quantitative data
4. Format diamond targets and contact info professionally

## Expected Result:
- **Before**: 65 Tavily calls per university
- **After**: 35 Tavily calls per university  
- **Savings**: 46% reduction in API usage
- **Quality**: Maintained through strategic query selection

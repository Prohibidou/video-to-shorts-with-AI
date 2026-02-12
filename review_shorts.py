"""
Review and manage shorts status (approved/rejected/pending).

Usage:
    python review_shorts.py                    # Show all shorts with status
    python review_shorts.py --url <URL>        # Show shorts for specific video URL
    python review_shorts.py --approve <ID>     # Approve a short
    python review_shorts.py --reject <ID>      # Reject a short
    python review_shorts.py --pending          # Show only pending shorts
    python review_shorts.py --status           # Summary by status
"""
import argparse
import sys
from database import (
    get_processed_segments, get_all_shorts, get_all_videos,
    approve_short, reject_short, update_short_status
)


def show_shorts(shorts: list[dict], title: str = "Shorts"):
    """Display shorts in a formatted table."""
    if not shorts:
        print(f"\n  No shorts found.\n")
        return
    
    print(f"\n{'='*80}")
    print(f"  {title} ({len(shorts)} total)")
    print(f"{'='*80}\n")
    
    for s in shorts:
        status_icon = {"approved": "✅", "rejected": "❌", "pending": "⏳"}.get(s["status"], "❓")
        hook = s.get("hook_text", "")
        hook_display = f' | Hook: "{hook[:50]}..."' if hook else ""
        
        print(f"  {status_icon} ID={s['id']:3d} | {s['start_time']}-{s['end_time']} | {s['status']:8s} | {s['title']}{hook_display}")
    
    print()


def show_status_summary():
    """Show count of shorts by status."""
    shorts = get_all_shorts()
    
    counts = {"approved": 0, "rejected": 0, "pending": 0}
    for s in shorts:
        status = s.get("status", "pending")
        counts[status] = counts.get(status, 0) + 1
    
    print(f"\n{'='*40}")
    print(f"  Shorts Status Summary")
    print(f"{'='*40}")
    print(f"  ✅ Approved:  {counts['approved']}")
    print(f"  ❌ Rejected:  {counts['rejected']}")
    print(f"  ⏳ Pending:   {counts['pending']}")
    print(f"  ─────────────────────")
    print(f"  📊 Total:     {sum(counts.values())}")
    print()
    
    # Show videos
    videos = get_all_videos()
    if videos:
        print(f"  Videos processed: {len(videos)}")
        for v in videos:
            title = v.get("title", "Unknown")[:50]
            print(f"    • {title}")
            print(f"      {v['url']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Review and manage shorts status")
    parser.add_argument("--url", type=str, help="Show shorts for a specific video URL")
    parser.add_argument("--approve", type=int, help="Approve a short by ID")
    parser.add_argument("--reject", type=int, help="Reject a short by ID")
    parser.add_argument("--pending", action="store_true", help="Show only pending shorts")
    parser.add_argument("--status", action="store_true", help="Show status summary")
    parser.add_argument("--reset", type=int, help="Reset a short to pending status by ID")
    
    args = parser.parse_args()
    
    # Action: approve
    if args.approve:
        approve_short(args.approve)
        print(f"  ✅ Short ID={args.approve} marked as APPROVED")
        return
    
    # Action: reject
    if args.reject:
        reject_short(args.reject)
        print(f"  ❌ Short ID={args.reject} marked as REJECTED")
        return
    
    # Action: reset to pending
    if args.reset:
        update_short_status(args.reset, 'pending')
        print(f"  ⏳ Short ID={args.reset} reset to PENDING")
        return
    
    # View: status summary
    if args.status:
        show_status_summary()
        return
    
    # View: by URL
    if args.url:
        shorts = get_processed_segments(args.url)
        show_shorts(shorts, f"Shorts for URL")
        return
    
    # View: pending only
    if args.pending:
        all_shorts = get_all_shorts()
        pending = [s for s in all_shorts if s.get("status") == "pending"]
        show_shorts(pending, "Pending Shorts")
        return
    
    # Default: show all
    all_shorts = get_all_shorts()
    show_shorts(all_shorts, "All Shorts")


if __name__ == "__main__":
    main()

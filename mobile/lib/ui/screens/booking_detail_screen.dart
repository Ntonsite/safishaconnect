import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../core/repository.dart';
import '../../l10n/app_localizations.dart';
import '../../models/models.dart';
import '../theme.dart';
import '../widgets/common.dart';

const _journey = [
  'CONFIRMED',
  'PROVIDER_ASSIGNED',
  'PROVIDER_EN_ROUTE',
  'PROVIDER_ARRIVED',
  'SERVICE_IN_PROGRESS',
  'COMPLETED_BY_PROVIDER',
  'CLOSED',
];

const _position = {
  'PENDING_CONFIRMATION': 0,
  'CONFIRMED': 1,
  'FINDING_PROVIDER': 1,
  'REASSIGNMENT_REQUIRED': 1,
  'PROVIDER_ASSIGNED': 1,
  'PROVIDER_EN_ROUTE': 2,
  'PROVIDER_ARRIVED': 3,
  'SERVICE_IN_PROGRESS': 4,
  'COMPLETED_BY_PROVIDER': 5,
  'DISPUTED': 5,
  'CUSTOMER_CONFIRMED': 6,
  'CLOSED': 6,
};

class BookingDetailScreen extends StatefulWidget {
  final String bookingId;
  final bool justCreated;
  const BookingDetailScreen({super.key, required this.bookingId, this.justCreated = false});

  @override
  State<BookingDetailScreen> createState() => _BookingDetailScreenState();
}

class _BookingDetailScreenState extends State<BookingDetailScreen> {
  BookingDetail? _booking;
  Object? _error;
  bool _busy = false;
  Timer? _poll;
  int _rating = 0;
  final _comment = TextEditingController();

  Repository get _repo => context.read<Repository>();

  @override
  void initState() {
    super.initState();
    _load();
    _poll = Timer.periodic(const Duration(seconds: 15), (_) {
      if (_booking != null && liveStatuses.contains(_booking!.status)) _load();
    });
  }

  @override
  void dispose() {
    _poll?.cancel();
    _comment.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final b = await _repo.booking(widget.bookingId);
      if (mounted) {
        setState(() {
          _booking = b;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = e);
    }
  }

  Future<void> _run(Future<void> Function() action, {String? success}) async {
    setState(() => _busy = true);
    try {
      await action();
      await _load();
      if (success != null && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(success)));
      }
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _cancel() async {
    final l = AppLocalizations.of(context);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l.cancelBooking),
        content: Text(l.cancelConfirm),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(l.keep)),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: Brand.red600),
            child: Text(l.cancelBooking),
          ),
        ],
      ),
    );
    if (ok == true) await _run(() => _repo.cancel(widget.bookingId));
  }

  Future<void> _reportIssue() async {
    final l = AppLocalizations.of(context);
    final description = TextEditingController();
    var category = 'QUALITY';
    final categories = [
      ('QUALITY', l.issueQuality),
      ('LATE_OR_NO_SHOW', l.issueLate),
      ('DAMAGE', l.issueDamage),
      ('CONDUCT', l.issueConduct),
      ('PAYMENT', l.issuePayment),
      ('OTHER', l.issueOther),
    ];
    final result = await showDialog<(String, String)>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: Text(l.reportIssue),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              DropdownButtonFormField<String>(
                initialValue: category,
                decoration: InputDecoration(labelText: l.issueCategory),
                items: [for (final item in categories) DropdownMenuItem(value: item.$1, child: Text(item.$2))],
                onChanged: (value) => setDialogState(() => category = value ?? category),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: description,
                maxLines: 4,
                maxLength: 2000,
                decoration: InputDecoration(labelText: l.issueDescription, helperText: l.issueDescriptionHint),
                onChanged: (_) => setDialogState(() {}),
              ),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: Text(l.back)),
            FilledButton(
              onPressed: description.text.trim().length < 10
                  ? null
                  : () => Navigator.pop(ctx, (category, description.text.trim())),
              child: Text(l.sendIssue),
            ),
          ],
        ),
      ),
    );
    description.dispose();
    if (result != null) {
      await _run(() => _repo.reportIssue(widget.bookingId, result.$1, result.$2), success: l.issueSent);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final b = _booking;
    return Scaffold(
      appBar: AppBar(title: Text(b?.reference ?? '')),
      body: b == null
          ? (_error != null ? ErrorRetry(error: _error!, onRetry: _load) : const Center(child: CircularProgressIndicator()))
          : RefreshIndicator(onRefresh: _load, child: _content(l, b)),
    );
  }

  Widget _content(AppLocalizations l, BookingDetail b) {
    final locale = Localizations.localeOf(context).languageCode;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      children: [
        if (widget.justCreated && (b.status == 'FINDING_PROVIDER' || b.status == 'REASSIGNMENT_REQUIRED')) ...[
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: Brand.green50,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Brand.green100),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Icon(Icons.check_circle, color: Brand.green700, size: 28),
                const SizedBox(width: 10),
                Expanded(child: Text(l.bookingConfirmed, style: Theme.of(context).textTheme.titleMedium)),
              ]),
              const SizedBox(height: 12),
              Text('${l.bookingReference}: ${b.reference}', style: const TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 4),
              Text('${b.serviceName(locale)} · ${formatDate(context, b.date)} · ${b.startTime}'),
              Text('${b.areaName} · ${formatMoney(b.total, b.currency)}'),
              const SizedBox(height: 10),
              Text(l.findingProvider, style: const TextStyle(color: Brand.ink2)),
            ]),
          ),
          const SizedBox(height: 12),
        ],
        Row(children: [
          ServiceBadge(b.serviceIcon),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(b.serviceName(locale), style: Theme.of(context).textTheme.titleLarge),
              Text('${formatDate(context, b.date)} · ${b.startTime}–${addMinutes(b.startTime, b.durationMinutes)}',
                  style: const TextStyle(color: Brand.ink3)),
            ]),
          ),
        ]),
        const SizedBox(height: 12),
        Align(alignment: Alignment.centerLeft, child: StatusChip(b.status)),
        const SizedBox(height: 16),

        if (b.can('CONFIRM_COMPLETION')) ...[
          SectionCard(
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text(l.confirmCompletionBody),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: _busy ? null : () => _run(() => _repo.confirmCompletion(b.id)),
                icon: const Icon(Icons.check_circle_outline),
                label: Text(l.confirmCompletion),
              ),
              if (b.can('REPORT_ISSUE')) ...[
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: _busy ? null : _reportIssue,
                  icon: const Icon(Icons.report_outlined),
                  label: Text(l.reportIssue),
                ),
              ],
            ]),
          ),
          const SizedBox(height: 12),
        ],
        if (b.can('REVIEW')) ...[
          SectionCard(title: l.rateTitle, child: _reviewForm(l, b)),
          const SizedBox(height: 12),
        ],
        if (b.review != null) ...[
          SectionCard(
            title: l.yourReview,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              _stars((b.review!['rating'] as num).toInt()),
              if ((b.review!['comment'] as String?)?.isNotEmpty ?? false) ...[
                const SizedBox(height: 6),
                Text(b.review!['comment']),
              ],
            ]),
          ),
          const SizedBox(height: 12),
        ],

        SectionCard(title: l.progress, child: _timeline(l, b)),
        const SizedBox(height: 12),
        SectionCard(title: l.yourCleaner, child: _provider(l, b)),
        const SizedBox(height: 12),
        SectionCard(
          title: l.details,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(b.addressLine ?? '', style: const TextStyle(fontWeight: FontWeight.w500)),
            if (b.landmark != null) Text(b.landmark!, style: const TextStyle(color: Brand.ink3)),
            Text(b.areaName, style: const TextStyle(color: Brand.ink3)),
            if (b.bathrooms > 0) ...[
              const SizedBox(height: 8),
              Text(l.rooms(b.bedrooms, b.bathrooms)),
            ],
          ]),
        ),
        const SizedBox(height: 12),
        SectionCard(
          title: l.priceBreakdown,
          child: Column(children: [
            PriceLines(
              lines: [for (final line in b.priceItems) (label: line.label(locale), quantity: line.quantity, amount: line.amount)],
              total: b.total,
              currency: b.currency,
            ),
            if (b.payment != null) ...[
              const SizedBox(height: 12),
              Row(children: [
                Expanded(child: Text('${l.payment}: ${l.cash}', style: const TextStyle(color: Brand.ink3, fontSize: 13))),
                Text(paymentLabel(l, b.payment!['status']),
                    style: TextStyle(
                        fontWeight: FontWeight.w600,
                        color: b.payment!['status'] == 'PAID' ? Brand.green700 : Brand.amber700)),
              ]),
            ],
          ]),
        ),
        if (b.can('CANCEL')) ...[
          const SizedBox(height: 20),
          OutlinedButton(
            onPressed: _busy ? null : _cancel,
            style: OutlinedButton.styleFrom(foregroundColor: Brand.red600, side: const BorderSide(color: Color(0xFFF0C9C3))),
            child: Text(l.cancelBooking),
          ),
        ],
      ],
    );
  }

  Widget _timeline(AppLocalizations l, BookingDetail b) {
    if (b.status == 'CANCELLED') {
      return Row(children: [
        const Icon(Icons.cancel, color: Brand.red600),
        const SizedBox(width: 10),
        Text(statusLabel(l, 'CANCELLED')),
      ]);
    }
    final position = _position[b.status] ?? 0;
    String? when(String status) {
      final events = b.history.where((h) => h.toStatus == status);
      return events.isEmpty ? null : DateFormat('d MMM, HH:mm').format(events.last.at);
    }

    return Column(
      children: [
        for (var i = 0; i < _journey.length; i++)
          () {
            final done = i < position || (i == position && b.status == 'CLOSED');
            final current = i == position && !done;
            final label = current ? statusLabel(l, b.status) : statusLabel(l, _journey[i]);
            final stamp = current ? when(b.status) : when(_journey[i]);
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(children: [
                Container(
                  width: 22,
                  height: 22,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: done ? Brand.green600 : Colors.white,
                    border: Border.all(color: done || current ? Brand.green600 : Brand.line, width: 2),
                  ),
                  child: done
                      ? const Icon(Icons.check, size: 13, color: Colors.white)
                      : current
                          ? const Center(child: CircleAvatar(radius: 4, backgroundColor: Brand.green600))
                          : null,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(label,
                      style: TextStyle(
                        fontWeight: done || current ? FontWeight.w600 : FontWeight.w400,
                        color: done || current ? Brand.ink : Brand.ink3,
                      )),
                ),
                if ((done || current) && stamp != null) Text(stamp, style: const TextStyle(fontSize: 12, color: Brand.ink3)),
              ]),
            );
          }(),
      ],
    );
  }

  Widget _provider(AppLocalizations l, BookingDetail b) {
    final p = b.provider;
    if (p == null) {
      return Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Icon(Icons.search, color: Brand.ink3),
        const SizedBox(width: 10),
        Expanded(child: Text(l.awaitingCleaner, style: const TextStyle(color: Brand.ink3))),
      ]);
    }
    final name = p['display_name'] as String;
    final ratingCount = p['rating_count'] as int? ?? 0;
    final rating = num.tryParse('${p['rating_average']}') ?? 0;
    final phone = p['phone'] as String?;
    return Row(children: [
      CircleAvatar(
        radius: 24,
        backgroundColor: Brand.green100,
        child: Text(name.split(' ').take(2).map((s) => s[0]).join(),
            style: const TextStyle(color: Brand.green900, fontWeight: FontWeight.w700)),
      ),
      const SizedBox(width: 12),
      Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(name, style: const TextStyle(fontWeight: FontWeight.w600)),
          Row(children: [
            const Icon(Icons.verified, size: 14, color: Brand.green600),
            const SizedBox(width: 4),
            Text(l.verified, style: const TextStyle(fontSize: 12, color: Brand.ink3)),
            if (ratingCount > 0) ...[
              const SizedBox(width: 8),
              const Icon(Icons.star, size: 14, color: Color(0xFFD69E2E)),
              Text(' ${rating.toStringAsFixed(1)} ($ratingCount)', style: const TextStyle(fontSize: 12)),
            ],
          ]),
        ]),
      ),
      if (phone != null)
        TextButton.icon(
          onPressed: () {
            Clipboard.setData(ClipboardData(text: phone));
            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(phone)));
          },
          icon: const Icon(Icons.phone_outlined, size: 18),
          label: Text(l.call),
        ),
    ]);
  }

  Widget _stars(int value, {ValueChanged<int>? onTap}) => Row(
        children: [
          for (var i = 1; i <= 5; i++)
            GestureDetector(
              onTap: onTap == null ? null : () => onTap(i),
              child: Padding(
                padding: const EdgeInsets.only(right: 4),
                child: Icon(i <= value ? Icons.star_rounded : Icons.star_outline_rounded,
                    color: const Color(0xFFD69E2E), size: onTap == null ? 22 : 38, semanticLabel: '$i / 5'),
              ),
            ),
        ],
      );

  Widget _reviewForm(AppLocalizations l, BookingDetail b) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _stars(_rating, onTap: (v) => setState(() => _rating = v)),
          const SizedBox(height: 12),
          TextField(controller: _comment, maxLines: 3, decoration: InputDecoration(labelText: l.rateComment)),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: _rating == 0 || _busy
                ? null
                : () => _run(
                      () => _repo.review(b.id, _rating, _comment.text.trim().isEmpty ? null : _comment.text.trim()),
                      success: l.thanksReview,
                    ),
            child: Text(l.submitReview),
          ),
        ],
      );
}

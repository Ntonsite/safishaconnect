import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../l10n/app_localizations.dart';
import '../theme.dart';

String formatMoney(num value, [String currency = 'TZS']) =>
    '$currency ${NumberFormat.decimalPattern('en').format(value.round())}';

String formatDate(BuildContext context, DateTime date) =>
    DateFormat.MMMEd(Localizations.localeOf(context).languageCode).format(date);

String formatDuration(BuildContext context, int minutes) {
  final l = AppLocalizations.of(context);
  if (minutes < 60) return l.minutes(minutes);
  return l.hoursMinutes(minutes ~/ 60, minutes % 60);
}

String addMinutes(String hhmm, int minutes) {
  final parts = hhmm.split(':').map(int.parse).toList();
  final total = (parts[0] * 60 + parts[1] + minutes).clamp(0, 23 * 60 + 59);
  return '${(total ~/ 60).toString().padLeft(2, '0')}:${(total % 60).toString().padLeft(2, '0')}';
}

String errorText(BuildContext context, Object error) {
  final l = AppLocalizations.of(context);
  if (error is ApiException) return error.isNetwork ? l.networkError : error.message;
  return l.genericError;
}

void showError(BuildContext context, Object error) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(errorText(context, error))));
}

String statusLabel(AppLocalizations l, String status) => switch (status) {
      'PENDING_CONFIRMATION' => l.statusPENDING_CONFIRMATION,
      'CONFIRMED' => l.statusCONFIRMED,
      'FINDING_PROVIDER' => l.statusFINDING_PROVIDER,
      'PROVIDER_ASSIGNED' => l.statusPROVIDER_ASSIGNED,
      'PROVIDER_EN_ROUTE' => l.statusPROVIDER_EN_ROUTE,
      'PROVIDER_ARRIVED' => l.statusPROVIDER_ARRIVED,
      'SERVICE_IN_PROGRESS' => l.statusSERVICE_IN_PROGRESS,
      'COMPLETED_BY_PROVIDER' => l.statusCOMPLETED_BY_PROVIDER,
      'CUSTOMER_CONFIRMED' => l.statusCUSTOMER_CONFIRMED,
      'CLOSED' => l.statusCLOSED,
      'CANCELLED' => l.statusCANCELLED,
      'REASSIGNMENT_REQUIRED' => l.statusREASSIGNMENT_REQUIRED,
      'DISPUTED' => l.statusDISPUTED,
      _ => status,
    };

String paymentLabel(AppLocalizations l, String status) => switch (status) {
      'PAID' => l.paymentPAID,
      'FAILED' => l.paymentFAILED,
      'REFUNDED' => l.paymentREFUNDED,
      'CANCELLED' => l.paymentCANCELLED,
      _ => l.paymentPENDING,
    };

class StatusChip extends StatelessWidget {
  final String status;
  const StatusChip(this.status, {super.key});

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = switch (status) {
      'CANCELLED' || 'DISPUTED' => (Brand.red50, Brand.red600),
      'FINDING_PROVIDER' || 'REASSIGNMENT_REQUIRED' => (Brand.amber50, Brand.amber700),
      'SERVICE_IN_PROGRESS' || 'COMPLETED_BY_PROVIDER' || 'CUSTOMER_CONFIRMED' => (Brand.green50, Brand.green700),
      'CLOSED' || 'PENDING_CONFIRMATION' => (const Color(0xFFF1F3F2), Brand.ink2),
      _ => (Brand.teal50, Brand.teal600),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
      child: Text(
        statusLabel(AppLocalizations.of(context), status),
        style: TextStyle(color: fg, fontSize: 12, fontWeight: FontWeight.w600),
      ),
    );
  }
}

IconData serviceIcon(String name) => switch (name) {
      'home' => Icons.home_outlined,
      'building' => Icons.business_outlined,
      'truck' => Icons.local_shipping_outlined,
      'sofa' => Icons.weekend_outlined,
      _ => Icons.auto_awesome_outlined,
    };

class ServiceBadge extends StatelessWidget {
  final String icon;
  final double size;
  const ServiceBadge(this.icon, {super.key, this.size = 48});

  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(color: Brand.green50, borderRadius: BorderRadius.circular(12)),
        child: Icon(serviceIcon(icon), color: Brand.green700, size: size * 0.48),
      );
}

class SectionCard extends StatelessWidget {
  final String? title;
  final Widget child;
  final EdgeInsets padding;
  const SectionCard({super.key, this.title, required this.child, this.padding = const EdgeInsets.all(18)});

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: padding,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (title != null) ...[
                Text(title!, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
              ],
              child,
            ],
          ),
        ),
      );
}

class EmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? body;
  final Widget? action;
  const EmptyState({super.key, required this.icon, required this.title, this.body, this.action});

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 24),
        child: Column(
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(color: Brand.green50, borderRadius: BorderRadius.circular(14)),
              child: Icon(icon, color: Brand.green700),
            ),
            const SizedBox(height: 12),
            Text(title, style: Theme.of(context).textTheme.titleMedium, textAlign: TextAlign.center),
            if (body != null) ...[
              const SizedBox(height: 6),
              Text(body!, style: const TextStyle(color: Brand.ink3), textAlign: TextAlign.center),
            ],
            if (action != null) ...[const SizedBox(height: 16), action!],
          ],
        ),
      );
}

class ErrorRetry extends StatelessWidget {
  final Object error;
  final VoidCallback onRetry;
  const ErrorRetry({super.key, required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) => EmptyState(
        icon: Icons.cloud_off_outlined,
        title: errorText(context, error),
        action: OutlinedButton(onPressed: onRetry, child: Text(AppLocalizations.of(context).retry)),
      );
}

class LanguageToggle extends StatelessWidget {
  final Locale value;
  final ValueChanged<Locale> onChanged;
  const LanguageToggle({super.key, required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) => SegmentedButton<String>(
        showSelectedIcon: false,
        style: SegmentedButton.styleFrom(
          visualDensity: VisualDensity.compact,
          selectedBackgroundColor: Brand.green50,
          selectedForegroundColor: Brand.green900,
        ),
        segments: const [
          ButtonSegment(value: 'en', label: Text('EN')),
          ButtonSegment(value: 'sw', label: Text('SW')),
        ],
        selected: {value.languageCode},
        onSelectionChanged: (s) => onChanged(Locale(s.first)),
      );
}

class Counter extends StatelessWidget {
  final int value;
  final int min;
  final int max;
  final ValueChanged<int> onChanged;
  final String label;
  const Counter({super.key, required this.value, required this.onChanged, required this.label, this.min = 0, this.max = 10});

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(child: Text(label, style: const TextStyle(fontWeight: FontWeight.w600))),
          Container(
            decoration: BoxDecoration(
              border: Border.all(color: const Color(0xFFD4D9D2)),
              borderRadius: BorderRadius.circular(12),
              color: Colors.white,
            ),
            child: Row(
              children: [
                IconButton(
                  tooltip: '$label −',
                  onPressed: value > min ? () => onChanged(value - 1) : null,
                  icon: const Icon(Icons.remove),
                ),
                SizedBox(
                  width: 28,
                  child: Text('$value', textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                ),
                IconButton(
                  tooltip: '$label +',
                  onPressed: value < max ? () => onChanged(value + 1) : null,
                  icon: const Icon(Icons.add),
                ),
              ],
            ),
          ),
        ],
      );
}

class PriceLines extends StatelessWidget {
  final List<({String label, int quantity, num amount})> lines;
  final num total;
  final String currency;
  const PriceLines({super.key, required this.lines, required this.total, this.currency = 'TZS'});

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Column(
      children: [
        for (final line in lines)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(
              children: [
                Expanded(child: Text(line.quantity > 1 ? '${line.label} × ${line.quantity}' : line.label)),
                Text(formatMoney(line.amount, currency)),
              ],
            ),
          ),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(
            children: [
              Expanded(child: Text(l.materialsLine)),
              Text(l.included, style: const TextStyle(color: Brand.green700, fontWeight: FontWeight.w600)),
            ],
          ),
        ),
        const Padding(padding: EdgeInsets.symmetric(vertical: 8), child: Divider()),
        Row(
          children: [
            Expanded(child: Text(l.total, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 17))),
            Text(formatMoney(total, currency), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 17)),
          ],
        ),
      ],
    );
  }
}

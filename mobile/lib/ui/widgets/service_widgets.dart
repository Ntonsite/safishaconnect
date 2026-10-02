import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../l10n/app_localizations.dart';
import '../../models/models.dart';
import '../../state/app_state.dart';
import '../theme.dart';
import 'common.dart';

class ServiceRow extends StatelessWidget {
  final Service service;
  final VoidCallback onTap;
  const ServiceRow({super.key, required this.service, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(Brand.radius),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ServiceBadge(service.icon, size: 44),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    service.name(lang),
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    service.summary(lang),
                    style: const TextStyle(color: Brand.ink3),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    l.fromPrice(formatMoney(service.basePrice)),
                    style: const TextStyle(
                      color: Brand.green700,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: Brand.ink3, size: 20),
          ],
        ),
      ),
    );
  }
}

Future<bool?> showServiceSheet(
  BuildContext context,
  Service service, {
  bool canSelect = true,
}) => showModalBottomSheet<bool>(
  context: context,
  isScrollControlled: true,
  useSafeArea: true,
  builder: (ctx) {
    final l = AppLocalizations.of(ctx);
    final lang = Localizations.localeOf(ctx).languageCode;
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        0,
        20,
        20 + MediaQuery.viewInsetsOf(ctx).bottom,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                ServiceBadge(service.icon),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    service.name(lang),
                    style: Theme.of(ctx).textTheme.titleLarge,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Text(l.serviceIncludes, style: Theme.of(ctx).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(localized(service.raw, 'description', lang)),
            const SizedBox(height: 20),
            Text(
              l.materialsIncluded,
              style: const TextStyle(color: Brand.green700),
            ),
            const SizedBox(height: 12),
            Text(
              l.fromPrice(formatMoney(service.basePrice)),
              style: Theme.of(ctx).textTheme.titleMedium,
            ),
            Text(l.fixedPrice, style: const TextStyle(color: Brand.ink3)),
            const SizedBox(height: 24),
            if (canSelect)
              FilledButton(
                key: const ValueKey('select-service'),
                onPressed: () => Navigator.pop(ctx, true),
                child: Text(l.selectService),
              ),
          ],
        ),
      ),
    );
  },
);

Future<void> showSupportSheet(BuildContext context) async {
  final brand = context.read<AppState>().brand;
  await showModalBottomSheet<void>(
    context: context,
    useSafeArea: true,
    isScrollControlled: true,
    builder: (ctx) {
      final l = AppLocalizations.of(ctx);
      final contacts = [
        brand['support_phone'],
        brand['support_email'],
      ].whereType<String>().where((v) => v.trim().isNotEmpty).toList();
      return Padding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(l.support, style: Theme.of(ctx).textTheme.titleLarge),
              const SizedBox(height: 12),
              Text(l.supportBody),
              const SizedBox(height: 16),
              if (contacts.isEmpty) Text(l.noSupportContact),
              for (final contact in contacts)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: SelectableText(
                    contact,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                ),
              if (contacts.isNotEmpty)
                TextButton.icon(
                  onPressed: () async {
                    await Clipboard.setData(
                      ClipboardData(text: contacts.join('\n')),
                    );
                    if (ctx.mounted) {
                      ScaffoldMessenger.of(
                        ctx,
                      ).showSnackBar(SnackBar(content: Text(l.contactDetails)));
                    }
                  },
                  icon: const Icon(Icons.copy_outlined),
                  label: Text(l.contactDetails),
                ),
            ],
          ),
        ),
      );
    },
  );
}

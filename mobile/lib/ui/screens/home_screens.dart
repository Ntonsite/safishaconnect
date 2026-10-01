import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/repository.dart';
import '../../l10n/app_localizations.dart';
import '../../models/models.dart';
import '../../state/app_state.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'booking_detail_screen.dart';
import 'booking_flow_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _tab = 0;
  final _homeKey = GlobalKey<_BookingListState>();
  final _bookingsKey = GlobalKey<_BookingListState>();

  Future<void> _book() async {
    final created = await Navigator.of(context).push<BookingDetail>(
      MaterialPageRoute(builder: (_) => const BookingFlowScreen()),
    );
    if (created != null && mounted) {
      _homeKey.currentState?.reload();
      _bookingsKey.currentState?.reload();
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => BookingDetailScreen(bookingId: created.id, justCreated: true)));
      _homeKey.currentState?.reload();
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final pages = [
      _HomeTab(listKey: _homeKey, onBook: _book),
      _BookingsTab(listKey: _bookingsKey),
      const _ProfileTab(),
    ];
    return Scaffold(
      body: SafeArea(child: IndexedStack(index: _tab, children: pages)),
      floatingActionButton: _tab == 2
          ? null
          : FloatingActionButton.extended(
              onPressed: _book,
              backgroundColor: Brand.green700,
              foregroundColor: Colors.white,
              icon: const Icon(Icons.add),
              label: Text(l.bookCleaning),
            ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) {
          setState(() => _tab = i);
          if (i == 0) _homeKey.currentState?.reload();
          if (i == 1) _bookingsKey.currentState?.reload();
        },
        destinations: [
          NavigationDestination(icon: const Icon(Icons.home_outlined), selectedIcon: const Icon(Icons.home), label: l.home),
          NavigationDestination(
              icon: const Icon(Icons.receipt_long_outlined), selectedIcon: const Icon(Icons.receipt_long), label: l.bookings),
          NavigationDestination(icon: const Icon(Icons.person_outline), selectedIcon: const Icon(Icons.person), label: l.profile),
        ],
      ),
    );
  }
}

class _HomeTab extends StatelessWidget {
  final GlobalKey<_BookingListState> listKey;
  final VoidCallback onBook;
  const _HomeTab({required this.listKey, required this.onBook});

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final me = context.watch<AppState>().me;
    return BookingList(
      key: listKey,
      scope: 'active',
      header: Padding(
        padding: const EdgeInsets.fromLTRB(4, 12, 4, 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l.hello(me?.firstName ?? ''), style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 6),
            Text(l.homeSubtitle, style: const TextStyle(color: Brand.ink3)),
            const SizedBox(height: 24),
            Text(l.upcoming.toUpperCase(),
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: .6, color: Brand.ink3)),
          ],
        ),
      ),
      empty: EmptyState(
        icon: Icons.event_available_outlined,
        title: l.noActive,
        body: l.noActiveBody,
        action: SizedBox(width: 220, child: FilledButton(onPressed: onBook, child: Text(l.bookCleaning))),
      ),
    );
  }
}

class _BookingsTab extends StatelessWidget {
  final GlobalKey<_BookingListState> listKey;
  const _BookingsTab({required this.listKey});

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return BookingList(
      key: listKey,
      scope: 'all',
      header: Padding(
        padding: const EdgeInsets.fromLTRB(4, 12, 4, 16),
        child: Text(l.bookings, style: Theme.of(context).textTheme.headlineMedium),
      ),
      empty: EmptyState(icon: Icons.receipt_long_outlined, title: l.noHistory),
    );
  }
}

class BookingList extends StatefulWidget {
  final String scope;
  final Widget header;
  final Widget empty;
  const BookingList({super.key, required this.scope, required this.header, required this.empty});

  @override
  State<BookingList> createState() => _BookingListState();
}

class _BookingListState extends State<BookingList> {
  late Future<List<BookingSummary>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<BookingSummary>> _load() => context.read<Repository>().bookings(widget.scope);

  void reload() => setState(() => _future = _load());

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      color: Brand.green700,
      onRefresh: () async {
        reload();
        await _future;
      },
      child: FutureBuilder<List<BookingSummary>>(
        future: _future,
        builder: (context, snap) {
          final children = <Widget>[widget.header];
          if (snap.connectionState != ConnectionState.done) {
            children.add(const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())));
          } else if (snap.hasError) {
            children.add(ErrorRetry(error: snap.error!, onRetry: reload));
          } else if (snap.data!.isEmpty) {
            children.add(Card(child: widget.empty));
          } else {
            children.add(Card(
              child: Column(
                children: [
                  for (final (i, b) in snap.data!.indexed) ...[
                    if (i > 0) const Divider(),
                    BookingTile(
                      booking: b,
                      onTap: () async {
                        await Navigator.of(context)
                            .push(MaterialPageRoute(builder: (_) => BookingDetailScreen(bookingId: b.id)));
                        reload();
                      },
                    ),
                  ],
                ],
              ),
            ));
          }
          children.add(const SizedBox(height: 96));
          return ListView(padding: const EdgeInsets.symmetric(horizontal: 16), children: children);
        },
      ),
    );
  }
}

class BookingTile extends StatelessWidget {
  final BookingSummary booking;
  final VoidCallback onTap;
  const BookingTile({super.key, required this.booking, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final locale = Localizations.localeOf(context).languageCode;
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            ServiceBadge(booking.serviceIcon, size: 44),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(booking.serviceName(locale), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
                  const SizedBox(height: 2),
                  Text('${formatDate(context, booking.date)} · ${booking.startTime} · ${booking.areaName}',
                      style: const TextStyle(color: Brand.ink3, fontSize: 13)),
                  const SizedBox(height: 8),
                  StatusChip(booking.status),
                ],
              ),
            ),
            Text(formatMoney(booking.total, booking.currency), style: const TextStyle(fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}

class _ProfileTab extends StatelessWidget {
  const _ProfileTab();

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final state = context.watch<AppState>();
    final me = state.me;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(4, 12, 4, 20),
          child: Text(l.profile, style: Theme.of(context).textTheme.headlineMedium),
        ),
        Card(
          child: ListTile(
            contentPadding: const EdgeInsets.all(16),
            leading: CircleAvatar(
              radius: 24,
              backgroundColor: Brand.green100,
              child: Text(
                (me?.fullName ?? '?').split(' ').where((p) => p.isNotEmpty).take(2).map((p) => p[0]).join(),
                style: const TextStyle(color: Brand.green900, fontWeight: FontWeight.w700),
              ),
            ),
            title: Text(me?.fullName ?? '', style: const TextStyle(fontWeight: FontWeight.w600)),
            subtitle: Text([me?.phone, me?.email].whereType<String>().join('\n')),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(child: Text(l.language, style: const TextStyle(fontWeight: FontWeight.w600))),
                LanguageToggle(value: state.locale, onChanged: state.setLocale),
              ],
            ),
          ),
        ),
        const SizedBox(height: 24),
        OutlinedButton.icon(
          onPressed: state.logout,
          icon: const Icon(Icons.logout),
          label: Text(l.signOut),
        ),
      ],
    );
  }
}

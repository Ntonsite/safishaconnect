import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';

import 'core/api_client.dart';
import 'core/config.dart';
import 'core/repository.dart';
import 'core/token_store.dart';
import 'l10n/app_localizations.dart';
import 'state/app_state.dart';
import 'ui/screens/auth_screens.dart';
import 'ui/screens/home_screens.dart';
import 'ui/theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final api = ApiClient(baseUrl: AppConfig.apiBaseUrl, tokens: SecureTokenStore());
  final repo = Repository(api);
  final state = AppState(repo, initialLocale: await AppState.savedLocale());
  runApp(SafishaApp(repo: repo, state: state));
  state.bootstrap();
}

class SafishaApp extends StatelessWidget {
  final Repository repo;
  final AppState state;
  const SafishaApp({super.key, required this.repo, required this.state});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<Repository>.value(value: repo),
        ChangeNotifierProvider<AppState>.value(value: state),
      ],
      child: Consumer<AppState>(
        builder: (context, app, _) => MaterialApp(
          title: AppConfig.appName,
          debugShowCheckedModeBanner: false,
          theme: buildTheme(),
          locale: app.locale,
          supportedLocales: AppLocalizations.supportedLocales,
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          home: switch (app.status) {
            AuthStatus.unknown => const _Splash(),
            AuthStatus.signedOut => const LoginScreen(),
            AuthStatus.signedIn => const HomeShell(),
          },
        ),
      ),
    );
  }
}

class _Splash extends StatelessWidget {
  const _Splash();

  @override
  Widget build(BuildContext context) => const Scaffold(
        backgroundColor: Brand.green700,
        body: Center(child: Icon(Icons.water_drop_outlined, color: Brand.green100, size: 56)),
      );
}

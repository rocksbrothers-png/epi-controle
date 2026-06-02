import 'package:dio/dio.dart';
import '../models/company.dart';

class CompaniesApi {
  const CompaniesApi(this._dio);
  final Dio _dio;

  Future<List<Company>> getCompanies() async {
    final res = await _dio.get<Map<String, dynamic>>('/api/companies');
    final items = (res.data?['items'] as List?) ?? [];
    return items
        .map((e) => Company.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

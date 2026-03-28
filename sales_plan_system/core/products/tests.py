import csv
import io

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

from .models import Brand, Category, ProductSKU
from .selectors import filtered_skus, paginated_skus

User = get_user_model()


class BrandModelTests(TestCase):
    def test_create_brand(self):
        brand = Brand.objects.create(name='L\'Oreal', code='LOR')
        self.assertEqual(str(brand), 'L\'Oreal')
        self.assertTrue(brand.is_active)

    def test_brand_code_unique(self):
        Brand.objects.create(name='Brand A', code='DUPLICATE')
        with self.assertRaises(Exception):
            Brand.objects.create(name='Brand B', code='DUPLICATE')


class CategoryModelTests(TestCase):
    def test_create_category(self):
        cat = Category.objects.create(name='Skincare', code='SKC')
        self.assertEqual(str(cat), 'Skincare')

    def test_category_hierarchy(self):
        parent = Category.objects.create(name='Beauty', code='BEA')
        child = Category.objects.create(name='Skincare', code='SKC', parent=parent)
        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())


class ProductSKUModelTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name='Test Brand', code='TB')
        self.category = Category.objects.create(name='Test Cat', code='TC')

    def test_create_sku(self):
        sku = ProductSKU.objects.create(
            sku_code='SKU001',
            sku_name='Test Product',
            brand=self.brand,
            category=self.category,
            unit_price=99.90,
        )
        self.assertEqual(str(sku), '[SKU001] Test Product')
        self.assertEqual(sku.status, ProductSKU.Status.ACTIVE)

    def test_is_active_property(self):
        sku = ProductSKU.objects.create(sku_code='SKU-A', sku_name='Active')
        self.assertTrue(sku.is_active)
        sku.status = ProductSKU.Status.INACTIVE
        sku.save()
        self.assertFalse(sku.is_active)

    def test_get_spec_display(self):
        sku = ProductSKU.objects.create(
            sku_code='SKU-S', sku_name='Spec Product',
            spec_info={'颜色': '红色', '容量': '50ml'},
        )
        self.assertIn('颜色:红色', sku.get_spec_display())
        self.assertIn('容量:50ml', sku.get_spec_display())

    def test_get_spec_display_empty(self):
        sku = ProductSKU.objects.create(sku_code='SKU-E', sku_name='Empty Spec')
        self.assertEqual(sku.get_spec_display(), '-')

    def test_sku_code_unique(self):
        ProductSKU.objects.create(sku_code='UNIQUE', sku_name='First')
        with self.assertRaises(Exception):
            ProductSKU.objects.create(sku_code='UNIQUE', sku_name='Second')


class SelectorTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name='B1', code='B1')
        self.brand2 = Brand.objects.create(name='B2', code='B2')
        self.category = Category.objects.create(name='C1', code='C1')
        ProductSKU.objects.create(sku_code='S1', sku_name='Alpha', brand=self.brand, category=self.category, status=ProductSKU.Status.ACTIVE)
        ProductSKU.objects.create(sku_code='S2', sku_name='Beta', brand=self.brand2, category=self.category, status=ProductSKU.Status.INACTIVE)

    def test_filtered_skus_all(self):
        qs = filtered_skus()
        self.assertEqual(qs.count(), 2)

    def test_filtered_skus_by_search(self):
        qs = filtered_skus(search='Alpha')
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().sku_code, 'S1')

    def test_filtered_skus_by_search_code(self):
        qs = filtered_skus(search='S2')
        self.assertEqual(qs.count(), 1)

    def test_filtered_skus_by_status(self):
        qs = filtered_skus(status=ProductSKU.Status.ACTIVE)
        self.assertEqual(qs.count(), 1)

    def test_filtered_skus_by_brand(self):
        qs = filtered_skus(brand_id=str(self.brand.pk))
        self.assertEqual(qs.count(), 1)

    def test_paginated_skus(self):
        page = paginated_skus(1, per_page=1)
        self.assertEqual(len(page), 1)
        self.assertTrue(page.has_next())


class SKUViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass1234')
        self.brand = Brand.objects.create(name='VB', code='VB')
        self.category = Category.objects.create(name='VC', code='VC')
        self.client.force_login(self.user)

    def test_sku_list_returns_200(self):
        response = self.client.get('/products/')
        self.assertEqual(response.status_code, 200)

    def test_sku_create(self):
        response = self.client.post('/products/create/', {
            'sku_code': 'NEW001',
            'sku_name': 'New Product',
            'brand': self.brand.pk,
            'category': self.category.pk,
            'unit_price': '50.00',
            'status': ProductSKU.Status.ACTIVE,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ProductSKU.objects.filter(sku_code='NEW001').exists())

    def test_sku_detail(self):
        sku = ProductSKU.objects.create(
            sku_code='D001', sku_name='Detail Test',
            brand=self.brand, category=self.category,
        )
        response = self.client.get(f'/products/{sku.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detail Test')

    def test_sku_edit(self):
        sku = ProductSKU.objects.create(
            sku_code='E001', sku_name='Edit Test',
            brand=self.brand, category=self.category,
        )
        response = self.client.post(f'/products/{sku.pk}/edit/', {
            'sku_code': 'E001',
            'sku_name': 'Edited Name',
            'brand': self.brand.pk,
            'category': self.category.pk,
            'unit_price': '75.00',
            'status': ProductSKU.Status.ACTIVE,
        })
        self.assertEqual(response.status_code, 302)
        sku.refresh_from_db()
        self.assertEqual(sku.sku_name, 'Edited Name')

    def test_sku_delete(self):
        sku = ProductSKU.objects.create(sku_code='DEL001', sku_name='Delete Me')
        response = self.client.post(f'/products/{sku.pk}/delete/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ProductSKU.objects.filter(pk=sku.pk).exists())

    def test_sku_list_search(self):
        ProductSKU.objects.create(sku_code='FIND', sku_name='Findable', brand=self.brand)
        response = self.client.get('/products/', {'search': 'Findable'})
        self.assertEqual(response.status_code, 200)

    def test_sku_list_htmx_returns_partial(self):
        response = self.client.get('/products/', HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)


class SKUImportExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='impuser', password='pass1234')
        self.client.force_login(self.user)

    def test_sku_import_csv(self):
        csv_content = 'sku_code,sku_name,brand_code,brand_name,category_code,category_name,unit_price,status\n'
        csv_content += 'IMP001,Imported Product,IMPB,Import Brand,IMPC,Import Cat,29.90,active\n'

        response = self.client.post('/products/import/', {
            'file': io.BytesIO(csv_content.encode('utf-8')),
        }, format='multipart')

        self.assertEqual(response.status_code, 302)
        sku = ProductSKU.objects.get(sku_code='IMP001')
        self.assertEqual(sku.sku_name, 'Imported Product')
        self.assertEqual(sku.brand.code, 'IMPB')
        self.assertEqual(sku.category.code, 'IMPC')

    def test_sku_import_updates_existing(self):
        Brand.objects.create(name='UB', code='UB')
        Category.objects.create(name='UC', code='UC')
        ProductSKU.objects.create(sku_code='UPD001', sku_name='Old Name')

        csv_content = 'sku_code,sku_name,brand_code,brand_name,category_code,category_name,unit_price\n'
        csv_content += 'UPD001,Updated Name,UB,UB,UC,UC,19.90\n'

        response = self.client.post('/products/import/', {
            'file': io.BytesIO(csv_content.encode('utf-8')),
        }, format='multipart')

        self.assertEqual(response.status_code, 302)
        sku = ProductSKU.objects.get(sku_code='UPD001')
        self.assertEqual(sku.sku_name, 'Updated Name')

    def test_sku_import_skips_empty_code(self):
        csv_content = 'sku_code,sku_name\n,Empty Code Row\nIMP002,Valid Row\n'
        response = self.client.post('/products/import/', {
            'file': io.BytesIO(csv_content.encode('utf-8')),
        }, format='multipart')

        self.assertEqual(response.status_code, 302)
        self.assertTrue(ProductSKU.objects.filter(sku_code='IMP002').exists())

    def test_sku_export_csv(self):
        brand = Brand.objects.create(name='EB', code='EB')
        cat = Category.objects.create(name='EC', code='EC')
        ProductSKU.objects.create(sku_code='EXP001', sku_name='Export Me', brand=brand, category=cat)

        response = self.client.get('/products/export/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

        content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        self.assertEqual(rows[0][0], 'SKU Code')
        self.assertTrue(any('EXP001' in row for row in rows))


class SKUSearchAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='apiuser', password='pass1234')
        self.client.force_login(self.user)
        self.brand = Brand.objects.create(name='SB', code='SB')
        self.category = Category.objects.create(name='SC', code='SC')
        ProductSKU.objects.create(sku_code='API001', sku_name='Searchable', brand=self.brand, category=self.category, status=ProductSKU.Status.ACTIVE)
        ProductSKU.objects.create(sku_code='API002', sku_name='Inactive One', status=ProductSKU.Status.INACTIVE)

    def test_search_api_returns_active_only(self):
        response = self.client.get('/products/api/search/', {'q': 'API'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['sku_code'], 'API001')

    def test_search_api_empty_query(self):
        response = self.client.get('/products/api/search/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertLessEqual(len(data['results']), 10)

    def test_search_api_by_name(self):
        response = self.client.get('/products/api/search/', {'q': 'Searchable'})
        data = response.json()
        self.assertEqual(len(data['results']), 1)

    def test_search_api_result_format(self):
        response = self.client.get('/products/api/search/', {'q': 'API001'})
        data = response.json()
        result = data['results'][0]
        self.assertIn('id', result)
        self.assertIn('text', result)
        self.assertIn('sku_code', result)
        self.assertIn('sku_name', result)
        self.assertIn('unit_price', result)

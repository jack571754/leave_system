import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.permissions.decorators import page_access_required
from .models import Brand, Category, ProductSKU
from .selectors import paginated_skus


@login_required
@page_access_required('products')
def sku_list(request):
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    brand_id = request.GET.get('brand', '')
    category_id = request.GET.get('category', '')
    page_obj = paginated_skus(
        request.GET.get('page', 1),
        search=search,
        status=status,
        brand_id=brand_id,
        category_id=category_id,
    )

    context = {
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'brand_id': brand_id,
        'category_id': category_id,
        'brands': Brand.objects.filter(is_active=True),
        'categories': Category.objects.filter(is_active=True),
        'status_choices': ProductSKU.Status.choices,
    }
    if request.htmx:
        return render(request, 'products/partials/sku_table.html', context)
    return render(request, 'products/sku_list.html', context)


@login_required
@page_access_required('products')
def sku_create(request):
    if request.method == 'POST':
        sku = ProductSKU.objects.create(
            sku_code=request.POST.get('sku_code'),
            sku_name=request.POST.get('sku_name'),
            brand_id=request.POST.get('brand') or None,
            category_id=request.POST.get('category') or None,
            spu_code=request.POST.get('spu_code', ''),
            spec_info=request.POST.get('spec_info', {}),
            unit=request.POST.get('unit', 'pcs'),
            unit_price=request.POST.get('unit_price') or 0,
            cost_price=request.POST.get('cost_price') or 0,
            status=request.POST.get('status', ProductSKU.Status.ACTIVE),
            remark=request.POST.get('remark', ''),
        )
        messages.success(request, f'SKU {sku.sku_code} created.')
        return redirect('products:sku_list')

    context = {
        'brands': Brand.objects.filter(is_active=True),
        'categories': Category.objects.filter(is_active=True),
        'status_choices': ProductSKU.Status.choices,
    }
    return render(request, 'products/sku_form.html', context)


@login_required
@page_access_required('products')
def sku_detail(request, pk):
    return render(request, 'products/sku_detail.html', {'sku': get_object_or_404(ProductSKU, pk=pk)})


@login_required
@page_access_required('products')
def sku_edit(request, pk):
    sku = get_object_or_404(ProductSKU, pk=pk)
    if request.method == 'POST':
        sku.sku_code = request.POST.get('sku_code')
        sku.sku_name = request.POST.get('sku_name')
        sku.brand_id = request.POST.get('brand') or None
        sku.category_id = request.POST.get('category') or None
        sku.spu_code = request.POST.get('spu_code', '')
        sku.unit = request.POST.get('unit', 'pcs')
        sku.unit_price = request.POST.get('unit_price', 0)
        sku.cost_price = request.POST.get('cost_price', 0)
        sku.status = request.POST.get('status', ProductSKU.Status.ACTIVE)
        sku.remark = request.POST.get('remark', '')
        sku.save()
        messages.success(request, f'SKU {sku.sku_code} updated.')
        return redirect('products:sku_detail', pk=sku.pk)

    context = {
        'sku': sku,
        'brands': Brand.objects.filter(is_active=True),
        'categories': Category.objects.filter(is_active=True),
        'status_choices': ProductSKU.Status.choices,
    }
    return render(request, 'products/sku_form.html', context)


@login_required
@page_access_required('products')
def sku_delete(request, pk):
    sku = get_object_or_404(ProductSKU, pk=pk)
    sku_code = sku.sku_code
    sku.delete()
    messages.success(request, f'SKU {sku_code} deleted.')
    return redirect('products:sku_list')


@login_required
@page_access_required('products')
def sku_import(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        decoded_file = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded_file))

        created_count = 0
        updated_count = 0
        for row in reader:
            sku_code = row.get('sku_code', '').strip()
            if not sku_code:
                continue

            brand, _ = Brand.objects.get_or_create(
                code=row.get('brand_code', sku_code[:4]),
                defaults={'name': row.get('brand_name', 'Default Brand')},
            )
            category, _ = Category.objects.get_or_create(
                code=row.get('category_code', 'default'),
                defaults={'name': row.get('category_name', 'Default Category')},
            )
            _, created = ProductSKU.objects.update_or_create(
                sku_code=sku_code,
                defaults={
                    'sku_name': row.get('sku_name', ''),
                    'brand': brand,
                    'category': category,
                    'unit_price': row.get('unit_price', 0),
                    'status': row.get('status', ProductSKU.Status.ACTIVE),
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        messages.success(request, f'Import complete: created {created_count}, updated {updated_count}.')
        return redirect('products:sku_list')

    return render(request, 'products/sku_import.html')


@login_required
@page_access_required('products')
def sku_export(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sku_export.csv"'
    writer = csv.writer(response)
    writer.writerow(['SKU Code', 'SKU Name', 'Brand', 'Category', 'Unit Price', 'Status'])
    for sku in ProductSKU.objects.select_related('brand', 'category'):
        writer.writerow([
            sku.sku_code,
            sku.sku_name,
            sku.brand.name if sku.brand else '',
            sku.category.name if sku.category else '',
            sku.unit_price,
            sku.get_status_display(),
        ])
    return response


@login_required
@page_access_required('products')
def sku_search_api(request):
    query = request.GET.get('q', '')
    skus = ProductSKU.objects.filter(status=ProductSKU.Status.ACTIVE)
    if query:
        skus = skus.filter(Q(sku_code__icontains=query) | Q(sku_name__icontains=query))[:10]

    data = [{
        'id': sku.id,
        'text': f'{sku.sku_code} - {sku.sku_name}',
        'sku_code': sku.sku_code,
        'sku_name': sku.sku_name,
        'unit_price': str(sku.unit_price),
    } for sku in skus]
    return JsonResponse({'results': data})
